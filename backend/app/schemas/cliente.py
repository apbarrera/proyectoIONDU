"""Datos de entrada y salida de clientes (docs/API.md, sección 7)."""

from typing import Annotated, Literal

from pydantic import StringConstraints

from app.schemas.common import (ApiInput, ApiModel, Text20, Text255)

IdentificationType = Literal["cedula", "ruc", "pasaporte", "exterior"]

Email = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=150, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
]
Phone = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=20, pattern=r"^[0-9+()\s-]*$")
]


class CustomerCreate(ApiInput):
    identification_type: IdentificationType | None = None  # se deduce de 10 o 13 dígitos
    identification: Text20
    name: Text255
    address: str | None = None
    phone: Phone | None = None
    email: Email | None = None


class CustomerUpdate(ApiInput):
    """Solo los campos enviados se modifican."""

    identification_type: IdentificationType | None = None
    identification: Text20 | None = None
    name: Text255 | None = None
    address: str | None = None
    phone: Phone | None = None
    email: Email | None = None


class Customer(ApiModel):
    id: int
    identification_type: IdentificationType
    identification: str
    name: str
    address: str | None
    phone: str | None
    email: str | None
    identification_warning: str | None
