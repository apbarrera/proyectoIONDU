"""Indicadores del dashboard financiero (RF-5.1 a 5.5).

Se calculan en vivo en cada consulta: así reflejan al instante cualquier venta, gasto o
movimiento confirmado (RF-5.4) sin tener que mantener una tabla de resumen.
"""

from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import TIMEZONE
from app.core.errors import UnprocessableError
from app.repositories.dashboard import DashboardRepository
from app.schemas.dashboard import (
    CategoryTotal,
    DailyPoint,
    DashboardSummary,
    InventoryStatus,
    LowStockProduct,
    TopProduct,
)
from app.services.venta import _rango_del_dia

MAX_DIAS = 366
_ZONA = ZoneInfo(TIMEZONE)
_CENTAVO = Decimal("0.01")


def _dinero(valor) -> Decimal:
    return Decimal(valor or 0).quantize(_CENTAVO, rounding=ROUND_HALF_UP)


def _periodo(desde: date | None, hasta: date | None) -> tuple[date, date]:
    """Por defecto, el mes en curso (en Ecuador) hasta hoy."""
    hoy = datetime.now(_ZONA).date()
    hasta = hasta or hoy
    desde = desde or hasta.replace(day=1)
    if desde > hasta:
        raise UnprocessableError(
            "La fecha inicial no puede ser posterior a la final.",
            details=[{"field": "from", "message": "Debe ser anterior o igual a 'to'."}],
        )
    if (hasta - desde).days + 1 > MAX_DIAS:
        raise UnprocessableError(
            f"El período puede tener como máximo {MAX_DIAS} días.",
            details=[{"field": "from", "message": f"Máximo {MAX_DIAS} días."}],
        )
    return desde, hasta


class DashboardService:
    def __init__(self, db: Session, empresa_id: int):
        self._repo = DashboardRepository(db, empresa_id)

    def resumen(self, desde: date | None = None, hasta: date | None = None) -> DashboardSummary:
        desde, hasta = _periodo(desde, hasta)
        inicio, fin = _rango_del_dia(desde, hasta)

        ingresos, ventas = self._repo.totales_ventas(inicio, fin)
        egresos, gastos = self._repo.totales_gastos(inicio, fin)
        por_dia_ventas = self._repo.ventas_por_dia(inicio, fin)
        por_dia_gastos = self._repo.gastos_por_dia(inicio, fin)

        dias = [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]
        activos, valor = self._repo.resumen_inventario()
        bajos, total_bajos = self._repo.stock_bajo()

        return DashboardSummary(
            from_=desde,
            to=hasta,
            income=_dinero(ingresos),
            expenses=_dinero(egresos),
            profit=_dinero(ingresos - egresos),
            sales_count=ventas,
            expenses_count=gastos,
            average_ticket=_dinero(ingresos / ventas) if ventas else _dinero(0),
            top_products=[
                TopProduct(product_id=i, name=n, units_sold=u, revenue=_dinero(r))
                for i, n, u, r in self._repo.productos_mas_vendidos(inicio, fin)
            ],
            daily_series=[
                DailyPoint(
                    date=dia,
                    income=_dinero(por_dia_ventas.get(dia)),
                    expenses=_dinero(por_dia_gastos.get(dia)),
                )
                for dia in dias
            ],
            expenses_by_category=[
                CategoryTotal(category_id=i, name=n, total=_dinero(t))
                for i, n, t in self._repo.gastos_por_categoria(inicio, fin)
            ],
            inventory=InventoryStatus(
                active_products=activos,
                low_stock_count=total_bajos,
                inventory_value=_dinero(valor),
                low_stock_products=[
                    LowStockProduct(
                        product_id=p.id_producto,
                        name=p.nombre,
                        unit=p.unidad_medida,
                        current_stock=p.stock_actual,
                        min_stock=p.stock_minimo,
                    )
                    for p in bajos
                ],
            ),
        )
