"""Datos de salida de facturas electrónicas."""

from datetime import datetime
from typing import Literal

from app.schemas.common import Amount, ApiModel

InvoiceStatus = Literal[
    "autorizada",
    "rechazada",
    "por_enviar",
    "por_autorizar",
]


class InvoiceMessage(ApiModel):
    identifier: str
    message: str
    additional_information: str | None
    type: Literal["ERROR", "ADVERTENCIA", "INFORMATIVO"]


class Invoice(ApiModel):
    id: int
    sale_id: int
    invoice_number: str
    access_key: str
    authorization_status: InvoiceStatus
    authorization_number: str | None
    authorization_date: datetime | None
    messages: list[InvoiceMessage]
    issue_date: datetime
    subtotal: Amount
    taxes: Amount
    total: Amount
