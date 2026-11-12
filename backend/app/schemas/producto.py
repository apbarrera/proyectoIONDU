"""Datos de entrada y salida de categorías y productos (docs/API.md, secciones 3 y 4)."""

from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.schemas.common import (
    Amount,
    ApiInput,
    ApiModel,
    OptionalText255,
    Text25,
    Text20,
    Text100,
    Text150,
)

# Provisional (RF-4.1), pendiente de decisión del equipo: ver docs/DECISIONES.md, sección 7.
ProductType = Literal["venta", "insumo", "ambos"]
VatPercentageCode = Literal["0", "4", "5", "6", "7"]


# ---------- Categorías ----------
class CategoryCreate(ApiInput):
    name: Text100
    description: OptionalText255 | None = None


class Category(ApiModel):
    id: int
    name: str
    description: str | None


# ---------- Productos ----------
# El XML de la factura del SRI admite máximo 25 caracteres en codigoPrincipal.
SKU_MAX = 25


class ProductCreate(ApiInput):
    sku: Text25
    name: Text150
    description: OptionalText255 | None = None
    category_id: int = Field(gt=0)
    type: ProductType = "venta"
    unit: Text20 = "UNIDAD"
    sale_price: Amount = Decimal("0")
    cost: Amount = Decimal("0")
    vat_percentage_code: VatPercentageCode = "4"
    current_stock: Amount = Decimal("0")
    min_stock: Amount | None = None


class ProductUpdate(ApiInput):
    """Solo los campos enviados se modifican. No incluye current_stock."""

    sku: Text25 | None = None
    name: Text150 | None = None
    description: OptionalText255 | None = None
    category_id: int | None = Field(default=None, gt=0)
    type: ProductType | None = None
    unit: Text20 | None = None
    sale_price: Amount | None = None
    cost: Amount | None = None
    vat_percentage_code: VatPercentageCode | None = None
    min_stock: Amount | None = None
    active: bool | None = None


class Product(ApiModel):
    id: int
    sku: str
    name: str
    description: str | None
    category_id: int
    category_name: str
    type: ProductType
    unit: str
    sale_price: Amount
    cost: Amount
    vat_percentage_code: VatPercentageCode
    applies_vat: bool
    current_stock: Amount
    min_stock: Amount | None
    low_stock: bool
    active: bool
