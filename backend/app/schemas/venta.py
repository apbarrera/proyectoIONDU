"""Datos de entrada y salida de ventas (docs/API.md, sección 8)."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.common import (
    Amount,
    ApiInput,
    ApiModel,
    OptionalText255,
    Quantity,
    Text255,
    UnitPrice,
)
from app.schemas.producto import VatPercentageCode

# La tarjeta se separa en débito y crédito porque el SRI las distingue.
PaymentMethod = Literal["efectivo", "tarjeta_debito", "tarjeta_credito", "transferencia"]
SaleStatus = Literal["completada", "anulada"]


class SaleItemCreate(ApiInput):
    """Línea de producto o servicio de una venta."""

    product_id: int | None = Field(default=None, gt=0)
    description: Text255 | None = None
    quantity: Quantity
    discount: Amount = Decimal("0")
    unit_price: UnitPrice | None = None
    vat_percentage_code: VatPercentageCode | None = None

    @model_validator(mode="after")
    def validar_tipo_de_linea(self):
        datos_servicio = (
            self.description,
            self.unit_price,
            self.vat_percentage_code,
        )

        if self.product_id is not None:
            if any(valor is not None for valor in datos_servicio):
                raise ValueError(
                    "Una línea de producto no puede incluir descripción, "
                    "precio ni código IVA manuales."
                )
        elif any(valor is None for valor in datos_servicio):
            raise ValueError(
                "Una línea de servicio requiere descripción, precio unitario "
                "y código de porcentaje IVA."
            )

        return self


class SaleCreate(ApiInput):
    """El precio y el IVA de productos los obtiene el backend."""

    customer_id: int | None = Field(default=None, gt=0)
    items: list[SaleItemCreate] = Field(min_length=1, max_length=200)
    payment_method: PaymentMethod
    observation: OptionalText255 | None = None


class SaleItem(ApiModel):
    product_id: int | None
    sku: str | None
    product_name: str
    quantity: Quantity
    unit_price: UnitPrice
    discount: Amount
    vat_percentage_code: VatPercentageCode
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
