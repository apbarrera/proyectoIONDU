"""Orquestación de emisión y persistencia de facturas electrónicas."""

import base64
import logging
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.cifrado import get_cifrador
from app.core.errors import (
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    UnprocessableError,
)
from app.models.empresa import Empresa
from app.models.factura import Factura as FacturaORM
from app.models.venta import Venta
from app.repositories.venta import VentaRepository
from app.schemas.configuracion_facturacion import ConfiguracionFacturacion
from app.services.almacenamiento import AlmacenamientoRideService
from app.services.secuencia_comprobante import SecuenciaComprobanteService
from app.sri.certificado import CertificadoInvalidoError
from app.sri.clave_acceso import Ambiente
from app.sri.factura_xml import (
    Comprador,
    DetalleFactura,
    Emisor,
    Pago,
    generar_factura_xml,
)
from app.sri.factura_xml import (
    Factura as FacturaSRI,
)
from app.sri.identificacion import TipoIdentificacion
from app.sri.ride import generar_ride
from app.sri.totales import (
    Linea,
    TarifaIva,
    TarifaIvaAplicada,
    calcular_totales,
)
from app.sri.xades import FirmadorXadesBes

logger = logging.getLogger(__name__)

TIMEZONE = ZoneInfo("America/Guayaquil")

TARIFAS_IVA_POR_CODIGO = {tarifa.codigo: tarifa for tarifa in TarifaIva}

TIPOS_IDENTIFICACION = {
    "cedula": TipoIdentificacion.CEDULA,
    "ruc": TipoIdentificacion.RUC,
    "pasaporte": TipoIdentificacion.PASAPORTE,
    "exterior": TipoIdentificacion.EXTERIOR,
}

FORMAS_PAGO = {
    "EFECTIVO": "01",
    "TARJETA_DEBITO": "16",
    "TARJETA_CREDITO": "19",
    "TRANSFERENCIA": "20",
}


def _decimal(valor) -> Decimal:
    return Decimal(str(valor))


def _dinero(valor: Decimal) -> Decimal:
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class FacturaService:
    """Emite una factura para una venta de la empresa del contexto actual."""

    def __init__(
        self,
        db: Session,
        empresa_id: int,
        almacenamiento: AlmacenamientoRideService | None = None,
    ):
        self.db = db
        self.empresa_id = empresa_id
        self.almacenamiento = almacenamiento
        self.ventas = VentaRepository(db, empresa_id)
        self.secuencias = SecuenciaComprobanteService(db)

    def emitir(self, id_venta: int) -> FacturaORM:
        """Prepara, persiste y envía una factura sin perder el XML ante fallos del SRI."""

        try:
            # Serializa la emisión concurrente de una misma venta sin
            # requerir privilegios UPDATE sobre la tabla venta.
            self.db.execute(
                select(
                    func.pg_advisory_xact_lock(
                        self.empresa_id,
                        id_venta,
                    )
                )
            )

            venta_bloqueada = self.db.scalar(
                select(Venta).where(
                    Venta.id_empresa == self.empresa_id,
                    Venta.id_venta == id_venta,
                )
            )

            if venta_bloqueada is None:
                raise NotFoundError("La venta solicitada no existe.")

            existente = self.db.scalar(
                select(FacturaORM).where(
                    FacturaORM.id_empresa == self.empresa_id,
                    FacturaORM.id_venta == id_venta,
                )
            )
            if existente is not None:
                raise ConflictError("La venta ya tiene una factura registrada.")

            if venta_bloqueada.estado != "COMPLETADA":
                raise ConflictError("Solo se pueden facturar ventas completadas.")

            empresa = self.db.get(Empresa, self.empresa_id)
            if empresa is None:
                raise NotFoundError("No se encontró la empresa.")

            configuracion = self._obtener_configuracion(empresa)
            firmador = self._obtener_firmador(empresa)

            fila = self.ventas.obtener(id_venta)
            if fila is None:
                raise NotFoundError("La venta solicitada no existe.")

            venta, cliente = fila[0], fila[1]
            detalles_venta = self.ventas.detalles([id_venta]).get(id_venta, [])

            if not detalles_venta:
                raise UnprocessableError("La venta no contiene detalles facturables.")

            lineas = []
            detalles_xml = []

            for detalle, producto in detalles_venta:
                tarifa = TARIFAS_IVA_POR_CODIGO.get(detalle.codigo_porcentaje_iva)
                if tarifa is None:
                    raise UnprocessableError("La venta contiene un código de IVA no reconocido.")

                porcentaje_guardado = getattr(detalle, "porcentaje_iva", None)
                porcentaje = (
                    _decimal(porcentaje_guardado)
                    if porcentaje_guardado is not None
                    else tarifa.porcentaje
                )
                tarifa_aplicada = TarifaIvaAplicada(
                    codigo=detalle.codigo_porcentaje_iva,
                    porcentaje=porcentaje,
                )

                linea = Linea(
                    cantidad=_decimal(detalle.cantidad),
                    precio_unitario=_decimal(detalle.precio_unitario),
                    tarifa=tarifa_aplicada,
                    descuento=_decimal(detalle.descuento),
                )
                lineas.append(linea)

                if producto is not None:
                    codigo = producto.codigo_principal
                    descripcion = producto.nombre
                    unidad = producto.unidad_medida
                else:
                    codigo = "SIN-CODIGO"
                    descripcion = detalle.descripcion_libre
                    unidad = None

                if not descripcion:
                    raise UnprocessableError(
                        "Una línea de la venta no tiene descripción para la factura."
                    )

                detalles_xml.append(
                    DetalleFactura(
                        codigo_principal=codigo or "SIN-CODIGO",
                        descripcion=descripcion,
                        linea=linea,
                        unidad_medida=unidad,
                    )
                )

            totales = calcular_totales(lineas)

            for (detalle, _producto), calculada in zip(
                detalles_venta,
                totales.lineas,
                strict=True,
            ):
                valor_iva_guardado = getattr(detalle, "valor_iva", None)
                if valor_iva_guardado is not None and _dinero(
                    _decimal(valor_iva_guardado)
                ) != _dinero(calculada.iva):
                    raise ConflictError(
                        "El IVA almacenado en una línea no coincide con "
                        "su cálculo histórico. No se emitió la factura."
                    )

            if (
                _dinero(totales.total_sin_impuestos) != _dinero(_decimal(venta.subtotal))
                or _dinero(totales.total_iva) != _dinero(_decimal(venta.iva))
                or _dinero(totales.importe_total) != _dinero(_decimal(venta.monto_total))
            ):
                raise ConflictError(
                    "Los totales de la venta no coinciden con el cálculo tributario. "
                    "No se emitió la factura."
                )

            comprador = self._construir_comprador(cliente)
            emisor = Emisor(
                ruc=empresa.ruc,
                razon_social=empresa.razon_social,
                dir_matriz=empresa.direccion,
                nombre_comercial=empresa.nombre_comercial,
                dir_establecimiento=configuracion.direccion_establecimiento,
                obligado_contabilidad=configuracion.obligado_contabilidad,
                contribuyente_especial=configuracion.contribuyente_especial,
                contribuyente_rimpe=configuracion.contribuyente_rimpe,
            )

            forma_pago_codigo = FORMAS_PAGO.get((venta.metodo_pago or "").upper())
            if forma_pago_codigo is None:
                raise UnprocessableError(
                    "El método de pago de la venta no tiene una equivalencia SRI."
                )

            from app.sri.factura_xml import FormaPago

            pago = Pago(
                forma=FormaPago(forma_pago_codigo),
                total=totales.importe_total,
            )

            fecha_emision = datetime.now(TIMEZONE)

            secuencial = self.secuencias.reservar(
                id_empresa=self.empresa_id,
                establecimiento=configuracion.establecimiento,
                punto_emision=configuracion.punto_emision,
                tipo_comprobante="01",
            )

            factura_sri = FacturaSRI(
                emisor=emisor,
                comprador=comprador,
                establecimiento=configuracion.establecimiento,
                punto_emision=configuracion.punto_emision,
                secuencial=secuencial,
                ambiente=Ambiente(configuracion.ambiente),
                detalles=detalles_xml,
                pagos=[pago],
                fecha_emision=fecha_emision.date(),
            )

            try:
                generada = generar_factura_xml(factura_sri)
                xml_firmado = firmador.firmar(generada.xml)
            except (ValueError, TypeError) as exc:
                raise UnprocessableError(f"No se pudo generar el comprobante: {exc}") from exc

            numero = (
                f"{configuracion.establecimiento}-{configuracion.punto_emision}-{secuencial:09d}"
            )

            factura = FacturaORM(
                id_empresa=self.empresa_id,
                id_venta=id_venta,
                numero_comprobante=numero,
                clave_acceso=generada.clave_acceso,
                estado_autorizacion="por_enviar",
                mensajes_sri=[],
                intentos_envio=0,
                subtotal=generada.totales.total_sin_impuestos,
                impuestos=generada.totales.total_iva,
                total=generada.totales.importe_total,
                fecha_emision=fecha_emision,
                xml_firmado=xml_firmado.decode("utf-8"),
            )
            self.db.add(factura)
            self.db.flush()
            self.db.commit()
            self.db.refresh(factura)

        except (NotFoundError, ConflictError, UnprocessableError):
            self.db.rollback()
            raise
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError(
                "No se pudo registrar la factura porque existe un comprobante con datos duplicados."
            ) from exc
        except Exception:
            self.db.rollback()
            raise

        # La factura ya está persistida. Un fallo de comunicación no debe
        # revertirla ni liberar el secuencial.
        return factura

    def obtener_ride(self, id_venta: int) -> bytes:
        """Descarga o reconstruye el RIDE sin volver a enviar la factura al SRI."""

        factura = self.db.scalar(
            select(FacturaORM).where(
                FacturaORM.id_empresa == self.empresa_id,
                FacturaORM.id_venta == id_venta,
            )
        )

        if factura is None:
            raise NotFoundError("No existe una factura para la venta solicitada.")

        if factura.estado_autorizacion != "autorizada" or not factura.xml_autorizado:
            raise ConflictError(
                "La factura todavía no está autorizada y no tiene un RIDE disponible."
            )

        if factura.pdf_ride_path and self.almacenamiento is not None:
            try:
                return self.almacenamiento.descargar(factura.pdf_ride_path)
            except (NotFoundError, ServiceUnavailableError):
                logger.warning(
                    "No se pudo descargar el RIDE de la factura %s; se reconstruirá.",
                    factura.id_factura,
                )

        try:
            contenido = generar_ride(
                factura.xml_autorizado.encode("utf-8"),
                numero_autorizacion=factura.numero_autorizacion,
                fecha_autorizacion=factura.fecha_autorizacion,
            )
        except Exception as exc:
            logger.exception(
                "No se pudo reconstruir el RIDE de la factura %s.",
                factura.id_factura,
            )
            raise UnprocessableError(
                "No fue posible reconstruir el PDF de la factura autorizada."
            ) from exc

        if self.almacenamiento is not None:
            try:
                ruta_ride = self.almacenamiento.guardar(
                    self.empresa_id,
                    factura.id_factura,
                    contenido,
                )
                factura.pdf_ride_path = ruta_ride
                self.db.commit()
            except ServiceUnavailableError:
                self.db.rollback()
                logger.warning(
                    "El RIDE de la factura %s se entregará sin almacenarlo.",
                    factura.id_factura,
                )
            except Exception:
                self.db.rollback()
                logger.exception(
                    "No se pudo registrar el RIDE reconstruido de la factura %s.",
                    factura.id_factura,
                )

        return contenido

    def _obtener_configuracion(self, empresa: Empresa) -> ConfiguracionFacturacion:
        if not empresa.datos_facturacion_electronica:
            raise UnprocessableError(
                "La empresa todavía no tiene configurada su facturación electrónica."
            )

        try:
            configuracion = ConfiguracionFacturacion.model_validate(
                empresa.datos_facturacion_electronica
            )
        except ValidationError as exc:
            raise UnprocessableError(
                "La configuración tributaria de la empresa está incompleta o es inválida."
            ) from exc

        if not empresa.ruc or not empresa.razon_social or not empresa.direccion:
            raise UnprocessableError(
                "La empresa debe tener RUC, razón social y dirección matriz registrados."
            )

        return configuracion

    def _obtener_firmador(self, empresa: Empresa) -> FirmadorXadesBes:
        if not empresa.certificado_p12_cifrado or not empresa.certificado_password_cifrada:
            raise UnprocessableError("La empresa no tiene un certificado electrónico configurado.")

        try:
            cifrador = get_cifrador()
            p12_cifrado = base64.b64decode(
                empresa.certificado_p12_cifrado,
                validate=True,
            )
            password_cifrada = base64.b64decode(
                empresa.certificado_password_cifrada,
                validate=True,
            )

            p12 = cifrador.descifrar(
                p12_cifrado,
                f"empresa:{self.empresa_id}:p12",
            )
            password = cifrador.descifrar(
                password_cifrada,
                f"empresa:{self.empresa_id}:p12_password",
            ).decode("utf-8")

            return FirmadorXadesBes.desde_p12(p12, password)

        except (CertificadoInvalidoError, ValueError, UnicodeDecodeError) as exc:
            raise UnprocessableError(
                "No se pudo validar el certificado electrónico almacenado."
            ) from exc
        except Exception as exc:
            raise ServiceUnavailableError(
                "No se pudo acceder al servicio de cifrado del certificado."
            ) from exc

    def _construir_comprador(self, cliente) -> Comprador:
        if cliente is None:
            return Comprador.consumidor_final()

        tipo = TIPOS_IDENTIFICACION.get(cliente.tipo_identificacion)
        if tipo is None:
            raise UnprocessableError(
                "El tipo de identificación del cliente no es válido para el SRI."
            )

        return Comprador(
            tipo_identificacion=tipo,
            identificacion=cliente.identificacion,
            razon_social=cliente.nombre_razon_social,
            direccion=cliente.direccion,
            correo=cliente.correo_electronico,
        )
