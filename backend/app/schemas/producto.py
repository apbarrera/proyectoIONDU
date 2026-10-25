"""Datos de entrada y salida de categorías y productos (docs/API.md, secciones 3 y 4)."""

from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.schemas.common import Amount, ApiInput, ApiModel, text_field

# Provisional (RF-4.1), pendiente de decisión del equipo: ver docs/DECISIONES.md, sección 7.
ProductType = Literal["venta", "insumo", "ambos"]


# ---------- Categorías ----------
class CategoryCreate(ApiInput):
    name: text_field(100)
    description: text_field(255, min_length=0) | None = None


class Category(ApiModel):
    id: int
    name: str
    description: str | None


# ---------- Productos ----------
class ProductCreate(ApiInput):
    sku: text_field(50)
    name: text_field(150)
    description: str | None = None
    category_id: int = Field(gt=0)
    type: ProductType = "venta"
    unit: text_field(20) = "UNIDAD"
    sale_price: Amount = Decimal("0")
    cost: Amount = Decimal("0")
    applies_vat: bool = True
    current_stock: Amount = Decimal("0")
    min_stock: Amount | None = None


class ProductUpdate(ApiInput):
    """Solo los campos enviados se modifican. No incluye current_stock: el stock cambia
    por ventas, compras y ajustes, nunca editando el producto."""

    sku: text_field(50) | None = None
    name: text_field(150) | None = None
    description: str | None = None
    category_id: int | None = Field(default=None, gt=0)
    type: ProductType | None = None
    unit: text_field(20) | None = None
    sale_price: Amount | None = None
    cost: Amount | None = None
    applies_vat: bool | None = None
    min_stock: Amount | None = None


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
    applies_vat: bool
    current_stock: Amount
    min_stock: Amount | None
    low_stock: bool
