"""Buzón de correo de facturas y borradores de gasto (RF-3.2, RF-3.3)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.schemas.common import ApiInput, ApiModel
from app.schemas.dashboard import Money
from app.schemas.gasto import ExpensePaymentMethod

Seguridad = Literal["ssl", "starttls", "ninguna"]
DraftStatus = Literal["pendiente", "convertido", "descartado"]


class EmailInbox(ApiModel):
    """La clave nunca se devuelve."""

    server: str
    port: int
    security: Seguridad
    username: str
    folder: str
    enabled: bool
    last_read_at: datetime | None
    last_error: str | None


class EmailInboxUpdate(ApiInput):
    server: str = Field(min_length=3, max_length=255, pattern=r"^[A-Za-z0-9.-]+$")
    port: int = Field(ge=1, le=65535)
    security: Seguridad = "ssl"
    username: str = Field(min_length=1, max_length=254)
    # Obligatoria la primera vez; si se omite al editar, se conserva la guardada.
    password: str | None = Field(default=None, min_length=1, max_length=500)
    folder: str = Field(default="INBOX", min_length=1, max_length=100)
    enabled: bool = True


class EmailInboxTestResult(ApiModel):
    ok: bool
    message: str


class ExpenseDraftLine(ApiModel):
    description: str
    quantity: Money
    total: Money


class ExpenseDraft(ApiModel):
    id: int
    received_at: datetime | None
    from_address: str | None
    subject: str | None
    supplier_ruc: str | None
    supplier_name: str | None
    receipt_number: str | None
    issue_date: date | None
    subtotal: Money | None
    iva_amount: Money | None
    total: Money | None
    lines: list[ExpenseDraftLine]
    status: DraftStatus
    expense_id: int | None


class ExpenseDraftConfirm(ApiInput):
    """Lo que el usuario confirma o corrige antes de crear el gasto (RF-3.3)."""

    category_id: int = Field(gt=0)
    total: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, min_length=1, max_length=1000)
    payment_method: ExpensePaymentMethod = "transferencia"
