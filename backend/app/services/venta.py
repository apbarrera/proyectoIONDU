"""Reglas de negocio de las ventas.

Registrar una venta es UNA transacción (todo o nada): venta, líneas,
descuento de stock y movimientos de inventario.
Los precios e IVA de productos salen del backend; los servicios utilizan
los datos proporcionados en la solicitud.
"""

import uuid
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import TIMEZONE
from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.models import DetalleVenta, MovimientoInventario, Producto, Venta
from app.repositories.cliente import ClienteRepository
from app.repositories.venta import VentaRepository
from app.schemas.common import Page
from app.schemas.factura import invoice_desde_factura
from app.schemas.venta import (
    PaymentMethod,
    Sale,
    SaleCreate,
    SaleItem,
    SaleStatus,
)
from app.sri.totales import Linea, TarifaIva, calcular_totales

CONSUMIDOR_FINAL = "CONSUMIDOR FINAL"
ORIGEN_MANUAL = "MANUAL"
MOVIMIENTO_VENTA = "VENTA"
MOVIMIENTO_ANULACION = "ANULACION_VENTA"  # devuelve el stock de una venta anulada
_ZONA = ZoneInfo(TIMEZONE)

# Relación entre el código de porcentaje del SRI y su tarifa.
TARIFAS_IVA_POR_CODIGO = {tarifa.codigo: tarifa for tarifa in TarifaIva}


def _metodo_pago_desde_db(valor: str) -> PaymentMethod:
    """Valida y convierte el método de pago almacenado en la base de datos."""
    metodos_validos: dict[str, PaymentMethod] = {
        "EFECTIVO": "efectivo",
        "TARJETA_DEBITO": "tarjeta_debito",
        "TARJETA_CREDITO": "tarjeta_credito",
        "TRANSFERENCIA": "transferencia",
    }

    try:
        return metodos_validos[valor.upper()]
    except KeyError as exc:
        raise ValueError(f"Método de pago no válido en la base de datos: {valor}") from exc


def _estado_desde_db(valor: str) -> SaleStatus:
    """Valida y convierte el estado almacenado en la base de datos."""
    estados_validos: dict[str, SaleStatus] = {
        "COMPLETADA": "completada",
        "ANULADA": "anulada",
    }

    try:
        return estados_validos[valor.upper()]
    except KeyError as exc:
        raise ValueError(f"Estado de venta no válido en la base de datos: {valor}") from exc


def _error(campo: str, mensaje: str, code: str) -> UnprocessableError:
    return UnprocessableError(
        mensaje,
        code=code,
        details=[{"field": campo, "message": mensaje}],
    )


def _a_sale(venta: Venta, cliente, lineas, factura=None, creado_por: str | None = None) -> Sale:
    return Sale(
        id=venta.id_venta,
        date=venta.fecha.astimezone(_ZONA),
        customer_id=venta.id_cliente,
        customer_name=cliente.nombre_razon_social if cliente else CONSUMIDOR_FINAL,
        customer_identification=cliente.identificacion if cliente else None,
        items=[
            SaleItem(
                product_id=detalle.id_producto,
                sku=producto.codigo_principal if producto else None,
                product_name=(producto.nombre if producto else (detalle.descripcion_libre or "")),
                quantity=detalle.cantidad,
                unit_price=detalle.precio_unitario,
                discount=detalle.descuento,
                vat_percentage_code=detalle.codigo_porcentaje_iva,
                subtotal=detalle.subtotal,
            )
            for detalle, producto in lineas
        ],
        subtotal=venta.subtotal,
        iva_amount=venta.iva,
        total=venta.monto_total,
        payment_method=_metodo_pago_desde_db(venta.metodo_pago),
        status=_estado_desde_db(venta.estado),
        observation=venta.observacion,
        created_by_id=venta.id_usuario,
        created_by=creado_por,
        invoice=invoice_desde_factura(factura) if factura else None,
    )


def _rango_del_dia(
    desde: date | None,
    hasta: date | None,
) -> tuple[datetime | None, datetime | None]:
    """Convierte días de Ecuador a un intervalo semiabierto."""
    inicio = datetime.combine(desde, time.min, _ZONA) if desde else None
    fin = datetime.combine(hasta + timedelta(days=1), time.min, _ZONA) if hasta else None
    return inicio, fin


class VentaService:
    def __init__(self, db: Session, empresa_id: int):
        self._db = db
        self._empresa_id = empresa_id
        self._repo = VentaRepository(db, empresa_id)
        self._clientes = ClienteRepository(db, empresa_id)

    # ---------- consultas ----------
    def listar(
        self,
        *,
        page: int,
        page_size: int,
        desde: date | None = None,
        hasta: date | None = None,
        customer_id: int | None = None,
        payment_method: PaymentMethod | None = None,
    ) -> Page[Sale]:
        inicio, fin = _rango_del_dia(desde, hasta)
        filas, total = self._repo.listar(
            desde=inicio,
            hasta=fin,
            id_cliente=customer_id,
            metodo_pago=payment_method.upper() if payment_method else None,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        lineas = self._repo.detalles([fila[0].id_venta for fila in filas])

        return Page[Sale](
            items=[_a_sale(v, c, lineas.get(v.id_venta, []), f, u) for v, c, f, u in filas],
            total=total,
            page=page,
            page_size=page_size,
        )

    def obtener(self, id_venta: int) -> Sale:
        encontrada = self._repo.obtener(id_venta)

        if encontrada is None:
            raise NotFoundError("La venta no existe.")

        venta, cliente, factura, creado_por = encontrada
        lineas = self._repo.detalles([id_venta]).get(id_venta, [])
        return _a_sale(venta, cliente, lineas, factura, creado_por)

    # ---------- anular (RF-2.7) ----------
    def anular(self, id_venta: int, motivo: str, id_usuario: uuid.UUID, quien: str | None) -> Sale:
        """Anula la venta: devuelve el stock y la conserva en el historial como `anulada`."""
        try:
            # El mismo candado que la emisión de facturas: no se anula mientras se factura.
            self._db.execute(select(func.pg_advisory_xact_lock(self._empresa_id, id_venta)))
            encontrada = self._repo.obtener(id_venta)
            if encontrada is None:
                raise NotFoundError("La venta no existe.")
            venta, _cliente, factura, _creado_por = encontrada
            if venta.estado == "ANULADA":
                raise ConflictError("La venta ya está anulada.", code="SALE_ALREADY_VOIDED")
            if factura is not None and factura.estado_autorizacion != "rechazada":
                raise ConflictError(
                    "La venta tiene una factura autorizada o en proceso en el SRI: se anula "
                    "emitiendo una nota de crédito, no desde aquí.",
                    code="SALE_HAS_INVOICE",
                )

            lineas = self._repo.detalles([id_venta]).get(id_venta, [])
            ids = sorted({d.id_producto for d, _ in lineas if d.id_producto is not None})
            productos = self._repo.bloquear_productos(ids)
            for detalle, _producto in lineas:
                producto = productos.get(detalle.id_producto)
                if producto is None:
                    continue  # línea de servicio: no mueve inventario
                producto.stock_actual += detalle.cantidad
                self._repo.agregar(
                    MovimientoInventario(
                        id_producto=producto.id_producto,
                        id_usuario=id_usuario,
                        tipo_movimiento=MOVIMIENTO_ANULACION,
                        cantidad=detalle.cantidad,
                        motivo=f"Anulación de venta #{id_venta}",
                    )
                )

            fecha = datetime.now(_ZONA).strftime("%d/%m/%Y %H:%M")
            nota = f"ANULADA el {fecha} por {quien or 'usuario'}: {motivo}"
            venta.observacion = (f"{venta.observacion} | {nota}" if venta.observacion else nota)[
                :255
            ]
            venta.estado = "ANULADA"
            self._repo.guardar_pendientes()
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        return self.obtener(id_venta)

    # ---------- registrar ----------
    def crear(self, datos: SaleCreate, id_usuario: uuid.UUID) -> Sale:
        try:
            resultado = self._crear_sin_confirmar(datos, id_usuario)
            self._db.commit()
            return resultado
        except Exception:
            self._db.rollback()
            raise

    def _crear_sin_confirmar(
        self,
        datos: SaleCreate,
        id_usuario: uuid.UUID,
    ) -> Sale:
        ids_productos = [item.product_id for item in datos.items if item.product_id is not None]

        if len(set(ids_productos)) != len(ids_productos):
            raise _error(
                "items",
                "Un producto no puede repetirse en la venta.",
                "DUPLICATE_PRODUCT",
            )

        if datos.customer_id is not None and self._clientes.obtener(datos.customer_id) is None:
            raise _error(
                "customerId",
                "El cliente no existe.",
                "CUSTOMER_NOT_FOUND",
            )

        productos = self._repo.bloquear_productos(ids_productos)
        self._validar_productos(datos, productos)

        lineas = []
        codigos_iva = []

        for i, item in enumerate(datos.items):
            if item.product_id is not None:
                producto = productos[item.product_id]
                codigo_iva = producto.codigo_porcentaje_iva
                precio_unitario = producto.precio_venta
                campo_codigo = f"items[{i}].productId"
            else:
                codigo_iva = item.vat_percentage_code
                precio_unitario = item.unit_price
                campo_codigo = f"items[{i}].vatPercentageCode"

            if codigo_iva is None:
                raise _error(
                    campo_codigo,
                    "El código de porcentaje IVA es obligatorio.",
                    "INVALID_VAT_CODE",
                )

            if precio_unitario is None:
                raise _error(
                    f"items[{i}].unitPrice",
                    "El precio unitario es obligatorio.",
                    "INVALID_UNIT_PRICE",
                )

            tarifa = TARIFAS_IVA_POR_CODIGO.get(codigo_iva)

            if tarifa is None:
                raise _error(
                    campo_codigo,
                    "El código de porcentaje IVA no es válido.",
                    "INVALID_VAT_CODE",
                )

            try:
                linea = Linea(
                    cantidad=item.quantity,
                    precio_unitario=precio_unitario,
                    tarifa=tarifa,
                    descuento=item.discount,
                )
            except ValueError as exc:
                raise _error(
                    f"items[{i}].discount",
                    str(exc),
                    "VALIDATION_ERROR",
                ) from exc

            lineas.append(linea)
            codigos_iva.append(codigo_iva)

        totales = calcular_totales(lineas)

        venta = Venta(
            id_usuario=id_usuario,
            id_cliente=datos.customer_id,
            subtotal=totales.total_sin_impuestos,
            iva=totales.total_iva,
            monto_total=totales.importe_total,
            tipo_origen=ORIGEN_MANUAL,
            metodo_pago=datos.payment_method.upper(),
            observacion=datos.observation or None,
            estado="COMPLETADA",
        )

        self._repo.agregar(venta)
        self._repo.guardar_pendientes()

        for item, calculada, codigo_iva in zip(
            datos.items,
            totales.lineas,
            codigos_iva,
            strict=True,
        ):
            producto = productos[item.product_id] if item.product_id is not None else None

            self._repo.agregar(
                DetalleVenta(
                    id_venta=venta.id_venta,
                    id_producto=producto.id_producto if producto else None,
                    descripcion_libre=(producto.nombre if producto else item.description),
                    cantidad=item.quantity,
                    precio_unitario=calculada.linea.precio_unitario,
                    descuento=item.discount,
                    codigo_porcentaje_iva=codigo_iva,
                    subtotal=calculada.precio_total_sin_impuesto,
                    porcentaje_iva=calculada.linea.tarifa.porcentaje,
                    valor_iva=calculada.iva,
                )
            )

            if producto is not None:
                producto.stock_actual -= item.quantity

                self._repo.agregar(
                    MovimientoInventario(
                        id_producto=producto.id_producto,
                        id_usuario=id_usuario,
                        tipo_movimiento=MOVIMIENTO_VENTA,
                        cantidad=item.quantity,
                        motivo=f"Venta #{venta.id_venta}",
                    )
                )

        # Hace visibles los detalles y movimientos antes de construir la respuesta.
        self._repo.guardar_pendientes()
        return self.obtener(venta.id_venta)

    def _validar_productos(
        self,
        datos: SaleCreate,
        productos: dict[int, Producto],
    ) -> None:
        sin_stock = []

        for i, item in enumerate(datos.items):
            if item.product_id is None:
                continue

            producto = productos.get(item.product_id)
            campo = f"items[{i}].productId"

            if producto is None:
                raise _error(
                    campo,
                    "El producto no existe.",
                    "PRODUCT_NOT_FOUND",
                )

            if not producto.activo:
                raise _error(
                    campo,
                    f"El producto {producto.nombre} está desactivado.",
                    "PRODUCT_INACTIVE",
                )

            if producto.tipo.upper() == "INSUMO":
                raise _error(
                    campo,
                    f"{producto.nombre} es un insumo y no se vende.",
                    "PRODUCT_NOT_SELLABLE",
                )

            if producto.stock_actual < item.quantity:
                disponible = f"{producto.stock_actual.normalize():f}"
                sin_stock.append(
                    {
                        "field": f"items[{i}].quantity",
                        "message": (f"Stock disponible de {producto.nombre}: {disponible}."),
                    }
                )

        if sin_stock:
            raise ConflictError(
                "No hay stock suficiente para registrar una venta.",
                code="INSUFFICIENT_STOCK",
                details=sin_stock,
            )
