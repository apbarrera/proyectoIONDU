"""Consultas de los indicadores del dashboard: todas filtran por la empresa.

Los totales se calculan en PostgreSQL (SUM/COUNT/GROUP BY), no trayendo filas a Python.
Los días se agrupan en hora de Ecuador: una venta a las 23:30 cuenta en ese día.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.core.config import TIMEZONE
from app.models import CategoriaGasto, DetalleVenta, Gasto, Producto, Venta

COMPLETADA = "COMPLETADA"
CONFIRMADO = "CONFIRMADO"


def _dia_ecuador(columna):
    return cast(func.timezone(TIMEZONE, columna), Date)


class DashboardRepository:
    def __init__(self, db: Session, empresa_id: int):
        self._db = db
        self._empresa_id = empresa_id

    def _ventas(self, inicio: datetime, fin: datetime):
        return (
            Venta.id_empresa == self._empresa_id,
            Venta.estado == COMPLETADA,
            Venta.fecha >= inicio,
            Venta.fecha < fin,
        )

    def _gastos(self, inicio: datetime, fin: datetime):
        return (
            Gasto.id_empresa == self._empresa_id,
            Gasto.estado == CONFIRMADO,
            Gasto.fecha >= inicio,
            Gasto.fecha < fin,
        )

    def totales_ventas(self, inicio: datetime, fin: datetime) -> tuple[Decimal, int]:
        total, cantidad = self._db.execute(
            select(func.coalesce(func.sum(Venta.monto_total), 0), func.count()).where(
                *self._ventas(inicio, fin)
            )
        ).one()
        return Decimal(total), cantidad

    def totales_gastos(self, inicio: datetime, fin: datetime) -> tuple[Decimal, int]:
        total, cantidad = self._db.execute(
            select(func.coalesce(func.sum(Gasto.monto), 0), func.count()).where(
                *self._gastos(inicio, fin)
            )
        ).one()
        return Decimal(total), cantidad

    def ventas_por_dia(self, inicio: datetime, fin: datetime) -> dict[date, Decimal]:
        dia = _dia_ecuador(Venta.fecha)
        filas = self._db.execute(
            select(dia, func.sum(Venta.monto_total)).where(*self._ventas(inicio, fin)).group_by(dia)
        )
        return dict(filas.all())

    def gastos_por_dia(self, inicio: datetime, fin: datetime) -> dict[date, Decimal]:
        dia = _dia_ecuador(Gasto.fecha)
        filas = self._db.execute(
            select(dia, func.sum(Gasto.monto)).where(*self._gastos(inicio, fin)).group_by(dia)
        )
        return dict(filas.all())

    def productos_mas_vendidos(self, inicio: datetime, fin: datetime, limite: int = 5):
        ingreso = func.sum(DetalleVenta.subtotal)
        return self._db.execute(
            select(
                Producto.id_producto,
                Producto.nombre,
                func.sum(DetalleVenta.cantidad),
                ingreso,
            )
            .join(
                Venta,
                (Venta.id_venta == DetalleVenta.id_venta)
                & (Venta.id_empresa == DetalleVenta.id_empresa),
            )
            .join(
                Producto,
                (Producto.id_producto == DetalleVenta.id_producto)
                & (Producto.id_empresa == DetalleVenta.id_empresa),
            )
            .where(*self._ventas(inicio, fin))
            .group_by(Producto.id_producto, Producto.nombre)
            .order_by(ingreso.desc(), Producto.nombre)
            .limit(limite)
        ).all()

    def gastos_por_categoria(self, inicio: datetime, fin: datetime):
        total = func.sum(Gasto.monto)
        return self._db.execute(
            select(CategoriaGasto.id_categoria_gasto, CategoriaGasto.nombre, total)
            .join(
                CategoriaGasto,
                (CategoriaGasto.id_categoria_gasto == Gasto.id_categoria_gasto)
                & (CategoriaGasto.id_empresa == Gasto.id_empresa),
            )
            .where(*self._gastos(inicio, fin))
            .group_by(CategoriaGasto.id_categoria_gasto, CategoriaGasto.nombre)
            .order_by(total.desc(), CategoriaGasto.nombre)
        ).all()

    # ---------- Inventario (estado actual, no depende del período) ----------
    def _activos(self):
        return (Producto.id_empresa == self._empresa_id, Producto.activo.is_(True))

    def resumen_inventario(self) -> tuple[int, Decimal]:
        cantidad, valor = self._db.execute(
            select(
                func.count(),
                func.coalesce(func.sum(Producto.stock_actual * Producto.precio_compra), 0),
            ).where(*self._activos())
        ).one()
        return cantidad, Decimal(valor)

    def stock_bajo(self, limite: int = 10) -> tuple[list[Producto], int]:
        condicion = (
            *self._activos(),
            Producto.stock_minimo.is_not(None),
            Producto.stock_actual <= Producto.stock_minimo,
        )
        total = self._db.scalar(select(func.count()).where(*condicion)) or 0
        # Los más críticos primero: los que están más lejos de su mínimo (en proporción).
        criticidad = Producto.stock_actual / func.nullif(Producto.stock_minimo, 0)
        productos = self._db.scalars(
            select(Producto)
            .where(*condicion)
            .order_by(criticidad.asc().nulls_last(), Producto.nombre)
            .limit(limite)
        )
        return list(productos), total
