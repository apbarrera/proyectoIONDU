"""Datos de entrada y salida de gastos, sus categorías y proveedores (docs/API.md, sección 11)."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.schemas.common import (
    Amount,
    ApiInput,
    ApiModel,
    OptionalText255,
    Text20,
    Text100,
    Text255,
)

ExpensePaymentMethod = Literal[
    "efectivo", "tarjeta_debito", "tarjeta_credito", "transferencia", "cheque"
]
Email = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=150, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
]
Text50 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Text1000 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
PositiveAmount = Annotated[Amount, Field(gt=0)]  # un gasto de $0 no tiene sentido
Phone = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=20, pattern=r"^[0-9+()\s-]*$")
]


# ---------- Categorías ----------
class ExpenseCategoryCreate(ApiInput):
    name: Text100
    description: OptionalText255 | None = None


class ExpenseCategory(ApiModel):
    id: int
    name: str
    description: str | None
    predefined: bool


# ---------- Proveedores ----------
class SupplierCreate(ApiInput):
    identification: Text20  # RUC (13 dígitos) o cédula (10)
    name: Text255
    phone: Phone | None = None
    email: Email | None = None
    address: str | None = None


class SupplierUpdate(ApiInput):
    identification: Text20 | None = None
    name: Text255 | None = None
    phone: Phone | None = None
    email: Email | None = None
    address: str | None = None


class Supplier(ApiModel):
    id: int
    identification: str
    name: str
    phone: str | None
    email: str | None
    address: str | None
    identification_warning: str | None


# ---------- Gastos ----------
class ExpenseCreate(ApiInput):
    category_id: int = Field(gt=0)
    supplier_id: int | None = Field(default=None, gt=0)
    total: PositiveAmount
    description: Text1000
    payment_method: ExpensePaymentMethod
    date: datetime | None = None  # por defecto, ahora
    receipt_number: Text50 | None = None


class ExpenseUpdate(ApiInput):
    category_id: int | None = Field(default=None, gt=0)
    supplier_id: int | None = Field(default=None, gt=0)
    total: PositiveAmount | None = None
    description: Text1000 | None = None
    payment_method: ExpensePaymentMethod | None = None
    date: datetime | None = None
    receipt_number: Text50 | None = None


class Expense(ApiModel):
    id: int
    date: datetime
    category_id: int
    category_name: str
    supplier_id: int | None
    supplier_name: str | None
    supplier_identification: str | None
    total: Amount
    description: str
    payment_method: ExpensePaymentMethod
    receipt_number: str | None
    status: Literal["confirmado", "borrador", "anulado"]
    source: Literal["manual", "correo"]
