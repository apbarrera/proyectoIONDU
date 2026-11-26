"""Schemas de la gestión de usuarios de la empresa (docs/API.md, sección 5)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.core.contrasenas import LONGITUD_MAXIMA, LONGITUD_MINIMA
from app.schemas.common import ApiInput, ApiModel

RolApi = Literal["admin", "operator"]


class CompanyUser(ApiModel):
    """Un usuario de la empresa seleccionada (mismos nombres que `User` del frontend)."""

    id: UUID
    email: str
    full_name: str
    role: RolApi
    active: bool
    created_at: datetime


class UserCreate(ApiInput):
    email: str = Field(min_length=3, max_length=254)
    full_name: str = Field(min_length=1, max_length=150)
    role: RolApi


class UserUpdate(ApiInput):
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    role: RolApi | None = None
    active: bool | None = None


class UserCreated(ApiModel):
    user: CompanyUser
    # Solo si se creó una cuenta nueva. Si el correo ya tenía cuenta (por otra empresa),
    # es null: la persona entra con su contraseña de siempre.
    temporary_password: str | None
    # Se envió por correo un enlace para que la persona elija su contraseña (SMTP_*).
    invitation_sent: bool = False


class PasswordReset(ApiModel):
    temporary_password: str


class PasswordChange(ApiInput):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=LONGITUD_MINIMA, max_length=LONGITUD_MAXIMA)
