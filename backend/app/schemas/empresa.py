"""Datos de la empresa y su configuración de facturación (docs/API.md, sección 10).

Los nombres siguen el modelo `Tenant` del frontend (core/models/tenant.model.ts).
"""

from datetime import date
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.schemas.common import ApiInput, ApiModel, OptionalText255, Text255

Email = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=150, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
]
TresDigitos = Annotated[str, StringConstraints(pattern=r"^[0-9]{3}$")]
Environment = Literal["pruebas", "produccion"]


class ElectronicSignature(ApiModel):
    configured: bool
    expires_at: date | None
    expires_soon: bool  # 30 días o menos para vencer (RNF-25)
    expired: bool


class BillingSettings(ApiModel):
    environment: Environment
    establishment: TresDigitos
    emission_point: TresDigitos
    required_to_keep_accounts: bool
    rimpe: bool
    special_taxpayer: str | None = None


class BillingSettingsUpdate(ApiInput, BillingSettings):
    special_taxpayer: (
        Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[0-9]{1,13}$")] | None
    ) = None


class Company(ApiModel):
    id: int
    ruc: str
    business_name: str
    trade_name: str | None
    economic_activity: str | None
    address: str | None
    email: str
    electronic_signature: ElectronicSignature
    billing: BillingSettings | None  # None: todavía no configura la facturación


class CompanyUpdate(ApiInput):
    """Solo los campos enviados se modifican. El RUC no se edita: va dentro de cada
    clave de acceso y cambiarlo rompería las facturas ya emitidas."""

    business_name: Text255 | None = None
    trade_name: OptionalText255 | None = None
    economic_activity: OptionalText255 | None = None
    address: Annotated[str, Field(max_length=500)] | None = None
    email: Email | None = None
