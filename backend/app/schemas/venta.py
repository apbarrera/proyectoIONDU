"""Datos de entrada y salida de ventas (docs/API.md, sección 8)."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.schemas.common import Amount, ApiInput, ApiModel, Quantity, UnitPrice, text_field

# La tarjeta se separa en débito y crédito porque el SRI las distingue (formas de pago 16 y 19).
PaymentMethod = Literal["efectivo", "tarjeta_debito", "tarjeta_credito", "transferencia"]
SaleStatus = Literal["completada", "anulada"]


class SaleItemCreate(ApiInput):
    product_id: int = Field(gt=0)
    quantity: Quantity
    discount: Amount = Decimal("0")


class SaleCreate(ApiInput):
    """El precio y el IVA no se envían: los pone el backend desde el producto."""

    customer_id: int | None = Field(default=None, gt=0)  # None = consumidor final
    items: list[SaleItemCreate] = Field(min_length=1, max_length=200)
    payment_method: PaymentMethod
    observation: text_field(255, min_length=0) | None = None


class SaleItem(ApiModel):
    product_id: int | None
    sku: str | None
    product_name: str
    quantity: Quantity
    unit_price: UnitPrice
    discount: Amount
    subtotal: Amount


class Sale(ApiModel):
    id: int
    date: datetime
    customer_id: int | None
    customer_name: str
    customer_identification: str | None
    items: list[SaleItem]
    subtotal: Amount
    iva_amount: Amount
    total: Amount
    payment_method: PaymentMethod
    status: SaleStatus
    observation: str | None
