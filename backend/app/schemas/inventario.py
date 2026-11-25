"""Movimientos de inventario y ajustes manuales (docs/API.md, sección 12).

Los nombres siguen los modelos del frontend (features/inventory/models).
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, PlainSerializer

from app.schemas.common import ApiInput, ApiModel, Quantity, Text255

MovementType = Literal["entrada", "salida", "ajuste", "venta", "anulacion"]

# Cantidad con signo: positiva si entra al inventario, negativa si sale.
SignedQuantity = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
Stock = Annotated[
    Decimal,
    Field(ge=0, max_digits=12, decimal_places=4),
    PlainSerializer(float, return_type=float, when_used="json"),
]


class MovementCreate(ApiInput):
    """Entrada o salida manual (RF-4.3): mercadería que llega, merma, consumo interno…"""

    product_id: int = Field(gt=0)
    type: Literal["entrada", "salida"]
    quantity: Quantity
    reason: Text255


class InventoryMovement(ApiModel):
    id: int
    product_id: int
    product_name: str
    unit: str
    type: MovementType
    quantity: SignedQuantity
    resulting_stock: SignedQuantity  # stock del producto justo después del movimiento
    reason: str | None
    date: datetime
    created_by: str | None  # nombre del usuario en la empresa


class AdjustmentCreate(ApiInput):
    """Ajuste contra el conteo físico (RF-4.8): se envía el stock real, no la diferencia."""

    product_id: int = Field(gt=0)
    new_stock: Stock
    reason: Text255


class StockAdjustment(ApiModel):
    id: int
    product_id: int
    product_name: str
    previous_stock: SignedQuantity
    new_stock: SignedQuantity
    quantity_delta: SignedQuantity
    reason: str
    date: datetime
    created_by: str | None
