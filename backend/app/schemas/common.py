"""Piezas comunes de los schemas de la API (ver docs/API.md, sección 1)."""

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, StringConstraints
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    """Base de los schemas: en Python snake_case, en el JSON camelCase (sale_price ↔ salePrice)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ApiInput(ApiModel):
    """Base de los cuerpos que envía el frontend: rechaza campos que no existen."""

    model_config = ConfigDict(extra="forbid")


# Montos y cantidades: NUMERIC(10,2) en la base; en el JSON salen como número (4.5), no como texto.
Amount = Annotated[
    Decimal,
    Field(ge=0, max_digits=10, decimal_places=2),
    PlainSerializer(float, return_type=float, when_used="json"),
]


# Cantidades y precios unitarios: NUMERIC(12,4) en la base (p. ej. 1.5 kg o $0.5555).
Quantity = Annotated[
    Decimal,
    Field(gt=0, max_digits=12, decimal_places=4),
    PlainSerializer(float, return_type=float, when_used="json"),
]
UnitPrice = Annotated[
    Decimal,
    Field(ge=0, max_digits=12, decimal_places=4),
    PlainSerializer(float, return_type=float, when_used="json"),
]


# Textos con longitud y normalización definidas estáticamente.
Text20 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
Text25 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=25)]
Text100 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Text150 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
Text255 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]

OptionalText255 = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=0, max_length=255),
]


class Page[T](ApiModel):
    """Igual que PageResult del frontend."""

    items: list[T]
    total: int
    page: int
    page_size: int
