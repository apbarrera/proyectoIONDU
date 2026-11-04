"""Consultas de ventas (patrón Repositorio): todas filtran por la empresa."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Cliente, DetalleVenta, MovimientoInventario, Producto, Venta


class VentaRepository:
    def __init__(self, db: Session, empresa_id: int):
        self._db = db
        self._empresa_id = empresa_id

    # ---------- escritura ----------
    def bloquear_productos(self, ids: Sequence[int]) -> dict[int, Producto]:
        """Productos de la empresa, BLOQUEADOS hasta el commit (SELECT ... FOR UPDATE).

        Así dos ventas simultáneas del mismo producto no pueden descontar el mismo
        stock. Se bloquean en orden de id para que dos ventas no se esperen entre sí
        (deadlock).
        """
        stmt = (
            select(Producto)
            .where(Producto.id_empresa == self._empresa_id, Producto.id_producto.in_(ids))
            .order_by(Producto.id_producto)
            .with_for_update()
        )
        return {p.id_producto: p for p in self._db.scalars(stmt)}

    def agregar(self, objeto: Venta | DetalleVenta | MovimientoInventario) -> None:
        if isinstance(objeto, (Venta, MovimientoInventario)):
            objeto.id_empresa = self._empresa_id
        self._db.add(objeto)

    def guardar_pendientes(self) -> None:
        self._db.flush()

    # ---------- lectura ----------
    def _con_cliente(self):
        return (
            select(Venta, Cliente)
            .outerjoin(
                Cliente,
                (Cliente.id_cliente == Venta.id_cliente) & (Cliente.id_empresa == Venta.id_empresa),
            )
            .where(Venta.id_empresa == self._empresa_id)
        )

    def listar(
        self,
        *,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        id_cliente: int | None = None,
        metodo_pago: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[tuple[Venta, Cliente | None]], int]:
        stmt = self._con_cliente()
        if desde is not None:
            stmt = stmt.where(Venta.fecha >= desde)
        if hasta is not None:
            stmt = stmt.where(Venta.fecha < hasta)
        if id_cliente is not None:
            stmt = stmt.where(Venta.id_cliente == id_cliente)
        if metodo_pago is not None:
            stmt = stmt.where(Venta.metodo_pago == metodo_pago)
        total = self._db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        filas = self._db.execute(
            stmt.order_by(Venta.fecha.desc(), Venta.id_venta.desc()).offset(offset).limit(limit)
        ).all()
        return [(fila[0], fila[1]) for fila in filas], total

    def obtener(self, id_venta: int) -> tuple[Venta, Cliente | None] | None:
        fila = self._db.execute(self._con_cliente().where(Venta.id_venta == id_venta)).first()
        return (fila[0], fila[1]) if fila else None

    def detalles(
        self, ids_venta: Sequence[int]
    ) -> dict[int, list[tuple[DetalleVenta, Producto | None]]]:
        """Líneas de varias ventas (de esta empresa), con su producto."""
        if not ids_venta:
            return {}
        stmt = (
            select(DetalleVenta, Producto)
            .join(Venta, Venta.id_venta == DetalleVenta.id_venta)
            .outerjoin(Producto, Producto.id_producto == DetalleVenta.id_producto)
            .where(Venta.id_empresa == self._empresa_id, DetalleVenta.id_venta.in_(ids_venta))
            .order_by(DetalleVenta.id_detalle_venta)
        )
        resultado: dict[int, list[tuple[DetalleVenta, Producto | None]]] = {}
        for detalle, producto in self._db.execute(stmt).all():
            resultado.setdefault(detalle.id_venta, []).append((detalle, producto))
        return resultado
