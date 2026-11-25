"""Consultas de movimientos de inventario: todas filtran por la empresa."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import MovimientoInventario, Producto, UsuarioEmpresa

# Tipos guardados en movimiento_inventario.tipo_movimiento. La cantidad siempre es > 0
# (restricción de la base); el tipo dice si entra o sale.
ENTRADA = "ENTRADA"
SALIDA = "SALIDA"
VENTA = "VENTA"
AJUSTE_ENTRADA = "AJUSTE_ENTRADA"
AJUSTE_SALIDA = "AJUSTE_SALIDA"
ANULACION_VENTA = "ANULACION_VENTA"  # devuelve el stock de una venta anulada
QUE_ENTRAN = (ENTRADA, AJUSTE_ENTRADA, ANULACION_VENTA)

Fila = tuple[MovimientoInventario, Producto, Decimal, str | None]


class InventarioRepository:
    def __init__(self, db: Session, empresa_id: int):
        self._db = db
        self._empresa_id = empresa_id

    def bloquear_producto(self, id_producto: int) -> Producto | None:
        """El producto de la empresa, BLOQUEADO hasta el commit (como en las ventas)."""
        return self._db.scalar(
            select(Producto)
            .where(Producto.id_empresa == self._empresa_id, Producto.id_producto == id_producto)
            .with_for_update()
        )

    def agregar(self, movimiento: MovimientoInventario) -> None:
        movimiento.id_empresa = self._empresa_id
        self._db.add(movimiento)
        self._db.flush()

    def _con_stock_resultante(self):
        """Movimientos con el stock que quedó después de cada uno.

        Se calcula hacia atrás desde el stock actual: stock después de un movimiento =
        stock actual − lo que movieron los posteriores. Así no depende de que el stock
        inicial del producto se haya registrado como movimiento.
        """
        m = MovimientoInventario
        con_signo = case((m.tipo_movimiento.in_(QUE_ENTRAN), m.cantidad), else_=-m.cantidad)
        posteriores = func.sum(con_signo).over(
            partition_by=m.id_producto,
            order_by=(m.fecha.desc(), m.id_movimiento.desc()),
            rows=(None, -1),  # todos los más nuevos, sin incluir este
        )
        return (
            select(
                m.id_movimiento,
                m.id_producto,
                m.tipo_movimiento,
                m.fecha,
                (Producto.stock_actual - func.coalesce(posteriores, 0)).label("stock"),
            )
            .join(
                Producto,
                (Producto.id_producto == m.id_producto) & (Producto.id_empresa == m.id_empresa),
            )
            .where(m.id_empresa == self._empresa_id)
        )

    def listar(
        self,
        *,
        id_producto: int | None = None,
        tipos: tuple[str, ...] | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Fila], int]:
        # Primero el cálculo sobre TODOS los movimientos y luego los filtros: si se
        # filtrara antes, el stock resultante no contaría los movimientos excluidos.
        base = self._con_stock_resultante()
        if id_producto is not None:  # filtrar por producto no cambia el cálculo
            base = base.where(MovimientoInventario.id_producto == id_producto)
        sub = base.subquery()
        stmt = select(sub.c.id_movimiento, sub.c.stock)
        if tipos:
            stmt = stmt.where(sub.c.tipo_movimiento.in_(tipos))
        if desde is not None:
            stmt = stmt.where(sub.c.fecha >= desde)
        if hasta is not None:
            stmt = stmt.where(sub.c.fecha < hasta)
        total = self._db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        ids = self._db.execute(
            stmt.order_by(sub.c.fecha.desc(), sub.c.id_movimiento.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return self._cargar(ids), total

    def obtener(self, id_movimiento: int) -> Fila | None:
        filas = self.listar_por_ids([id_movimiento])
        return filas[0] if filas else None

    def listar_por_ids(self, ids: list[int]) -> list[Fila]:
        sub = self._con_stock_resultante().subquery()
        pares = self._db.execute(
            select(sub.c.id_movimiento, sub.c.stock)
            .where(sub.c.id_movimiento.in_(ids))
            .order_by(sub.c.fecha.desc(), sub.c.id_movimiento.desc())
        ).all()
        return self._cargar(pares)

    def _cargar(self, pares) -> list[Fila]:
        """Trae los objetos completos manteniendo el orden y el stock calculado."""
        if not pares:
            return []
        stock = {id_: valor for id_, valor in pares}
        filas = self._db.execute(
            select(MovimientoInventario, Producto, UsuarioEmpresa.nombre_visible)
            .join(
                Producto,
                (Producto.id_producto == MovimientoInventario.id_producto)
                & (Producto.id_empresa == MovimientoInventario.id_empresa),
            )
            .outerjoin(
                UsuarioEmpresa,
                (UsuarioEmpresa.id_usuario == MovimientoInventario.id_usuario)
                & (UsuarioEmpresa.id_empresa == MovimientoInventario.id_empresa),
            )
            .where(
                MovimientoInventario.id_empresa == self._empresa_id,
                MovimientoInventario.id_movimiento.in_(stock),
            )
        ).all()
        por_id = {f[0].id_movimiento: f for f in filas}
        return [
            (por_id[i][0], por_id[i][1], stock[i], por_id[i][2]) for i, _ in pares if i in por_id
        ]
