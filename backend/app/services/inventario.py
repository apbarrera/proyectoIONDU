"""Reglas del inventario: historial, entradas y salidas manuales y ajustes (RF-4.3, 4.7, 4.8).

El stock de un producto solo cambia junto con un movimiento (DECISIONES 2.15), así el
historial siempre cuadra con el stock. Cada cambio bloquea el producto (SELECT ... FOR
UPDATE) igual que las ventas, para que dos operaciones a la vez no pisen el stock.
"""

import uuid
from datetime import date
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import TIMEZONE
from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.models import MovimientoInventario, Producto
from app.repositories.inventario import (
    AJUSTE_ENTRADA,
    AJUSTE_SALIDA,
    ENTRADA,
    QUE_ENTRAN,
    SALIDA,
    VENTA,
    Fila,
    InventarioRepository,
)
from app.schemas.common import Page
from app.schemas.inventario import (
    AdjustmentCreate,
    InventoryMovement,
    MovementCreate,
    MovementType,
    StockAdjustment,
)
from app.services.venta import _rango_del_dia

_ZONA = ZoneInfo(TIMEZONE)
_TIPOS_API = {
    ENTRADA: "entrada",
    SALIDA: "salida",
    VENTA: "venta",
    AJUSTE_ENTRADA: "ajuste",
    AJUSTE_SALIDA: "ajuste",
}
_TIPOS_BASE = {
    "entrada": (ENTRADA,),
    "salida": (SALIDA,),
    "venta": (VENTA,),
    "ajuste": (AJUSTE_ENTRADA, AJUSTE_SALIDA),
}


def _con_signo(m: MovimientoInventario):
    return m.cantidad if m.tipo_movimiento in QUE_ENTRAN else -m.cantidad


def _a_movimiento(fila: Fila) -> InventoryMovement:
    m, producto, stock, nombre = fila
    return InventoryMovement(
        id=m.id_movimiento,
        product_id=producto.id_producto,
        product_name=producto.nombre,
        unit=producto.unidad_medida,
        type=_TIPOS_API.get(m.tipo_movimiento, "ajuste"),
        quantity=_con_signo(m),
        resulting_stock=stock,
        reason=m.motivo,
        date=m.fecha.astimezone(_ZONA),
        created_by=nombre,
    )


def _a_ajuste(fila: Fila) -> StockAdjustment:
    m, producto, stock, nombre = fila
    delta = _con_signo(m)
    return StockAdjustment(
        id=m.id_movimiento,
        product_id=producto.id_producto,
        product_name=producto.nombre,
        previous_stock=stock - delta,
        new_stock=stock,
        quantity_delta=delta,
        reason=m.motivo or "",
        date=m.fecha.astimezone(_ZONA),
        created_by=nombre,
    )


class InventarioService:
    def __init__(self, db: Session, empresa_id: int):
        self._db = db
        self._repo = InventarioRepository(db, empresa_id)

    def listar(
        self,
        *,
        page: int,
        page_size: int,
        product_id: int | None = None,
        type: MovementType | None = None,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> Page[InventoryMovement]:
        inicio, fin = _rango_del_dia(desde, hasta)
        filas, total = self._repo.listar(
            id_producto=product_id,
            tipos=_TIPOS_BASE[type] if type else None,
            desde=inicio,
            hasta=fin,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return Page[InventoryMovement](
            items=[_a_movimiento(f) for f in filas], total=total, page=page, page_size=page_size
        )

    def _producto_bloqueado(self, id_producto: int) -> Producto:
        producto = self._repo.bloquear_producto(id_producto)
        if producto is None:
            mensaje = "El producto no existe."
            raise UnprocessableError(
                mensaje,
                code="PRODUCT_NOT_FOUND",
                details=[{"field": "productId", "message": mensaje}],
            )
        return producto

    def _registrar(
        self, producto: Producto, tipo: str, cantidad, motivo: str, id_usuario: uuid.UUID
    ) -> Fila:
        producto.stock_actual += cantidad if tipo in QUE_ENTRAN else -cantidad
        movimiento = MovimientoInventario(
            id_producto=producto.id_producto,
            id_usuario=id_usuario,
            tipo_movimiento=tipo,
            cantidad=cantidad,
            motivo=motivo,
        )
        self._repo.agregar(movimiento)
        fila = self._repo.obtener(movimiento.id_movimiento)
        self._db.commit()
        return fila

    def registrar_movimiento(
        self, datos: MovementCreate, id_usuario: uuid.UUID
    ) -> InventoryMovement:
        producto = self._producto_bloqueado(datos.product_id)
        if datos.type == "salida" and producto.stock_actual < datos.quantity:
            disponible = f"{producto.stock_actual.normalize():f}"
            raise ConflictError(
                f"No hay stock suficiente de {producto.nombre}: hay {disponible}.",
                code="INSUFFICIENT_STOCK",
                details=[{"field": "quantity", "message": f"Disponible: {disponible}."}],
            )
        tipo = ENTRADA if datos.type == "entrada" else SALIDA
        return _a_movimiento(
            self._registrar(producto, tipo, datos.quantity, datos.reason, id_usuario)
        )

    def ajustar(self, datos: AdjustmentCreate, id_usuario: uuid.UUID) -> StockAdjustment:
        producto = self._producto_bloqueado(datos.product_id)
        diferencia = datos.new_stock - producto.stock_actual
        if diferencia == 0:
            mensaje = "El stock ya es ese: no hay nada que ajustar."
            raise UnprocessableError(
                mensaje,
                code="NO_STOCK_CHANGE",
                details=[{"field": "newStock", "message": mensaje}],
            )
        tipo = AJUSTE_ENTRADA if diferencia > 0 else AJUSTE_SALIDA
        return _a_ajuste(self._registrar(producto, tipo, abs(diferencia), datos.reason, id_usuario))

    def obtener(self, id_movimiento: int) -> InventoryMovement:
        fila = self._repo.obtener(id_movimiento)
        if fila is None:
            raise NotFoundError("El movimiento no existe.")
        return _a_movimiento(fila)
