"""Indicadores del dashboard financiero (docs/API.md, sección 13).

Incluye los campos de `DashboardSummary` del frontend y los que pide RF-5.2.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import Field, PlainSerializer

from app.schemas.common import ApiModel

Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
Number = Money  # cantidades (pueden tener decimales: 1.5 kg)


class TopProduct(ApiModel):
    product_id: int
    name: str
    units_sold: Number
    revenue: Money  # subtotal sin IVA de sus líneas


class DailyPoint(ApiModel):
    date: date
    income: Money
    expenses: Money


class CategoryTotal(ApiModel):
    category_id: int
    name: str
    total: Money


class LowStockProduct(ApiModel):
    product_id: int
    name: str
    unit: str
    current_stock: Number
    min_stock: Number


class InventoryStatus(ApiModel):
    active_products: int
    low_stock_count: int
    inventory_value: Money  # stock × costo de los productos activos
    low_stock_products: list[LowStockProduct]  # los 10 más críticos


class DashboardSummary(ApiModel):
    from_: date = Field(alias="from")  # "from" es palabra reservada en Python
    to: date
    income: Money  # ventas completadas, con IVA
    expenses: Money  # gastos confirmados
    profit: Money  # utilidad estimada = ingresos − gastos
    sales_count: int
    expenses_count: int
    average_ticket: Money
    top_products: list[TopProduct]
    daily_series: list[DailyPoint]  # un punto por día del período, también los días en 0
    expenses_by_category: list[CategoryTotal]
    inventory: InventoryStatus
