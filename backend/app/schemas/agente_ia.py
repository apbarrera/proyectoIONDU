"""Schemas del agente de IA (docs/API.md, sección 15)."""

import datetime as dt
from typing import Literal

from pydantic import Field

from app.schemas.common import Amount, ApiInput, ApiModel
from app.schemas.gasto import ExpensePaymentMethod

AiActionStatus = Literal["pendiente", "confirmado", "corregido", "cancelado", "sin_propuesta"]


class AiMessageInput(ApiInput):
    text: str = Field(min_length=1, max_length=2000)


class AiExpenseProposal(ApiModel):
    total: Amount
    iva_amount: Amount
    category_id: int
    category_name: str
    description: str
    supplier_name: str | None
    payment_method: ExpensePaymentMethod
    date: dt.date | None


class AiProposal(ApiModel):
    type: Literal["expense"] = "expense"
    summary: str
    expense: AiExpenseProposal


class AiReply(ApiModel):
    """Respuesta a un mensaje. `actionId` solo si hay una propuesta por confirmar."""

    action_id: int | None
    reply: str
    proposal: AiProposal | None


class AiConfirm(ApiInput):
    """Correcciones opcionales antes de confirmar (RF-6.5 y RF-6.10, "Corregir")."""

    total: Amount | None = Field(default=None, gt=0)
    iva_amount: Amount | None = None
    category_id: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, min_length=1, max_length=300)
    payment_method: ExpensePaymentMethod | None = None
    date: dt.date | None = None


class AiConfirmResult(ApiModel):
    action_id: int
    status: AiActionStatus
    expense_id: int


class AiAction(ApiModel):
    """Historial del agente (RF-6.13)."""

    id: int
    timestamp: dt.datetime
    user_name: str
    instruction: str
    reply: str
    proposal: AiProposal | None
    status: AiActionStatus
    expense_id: int | None
