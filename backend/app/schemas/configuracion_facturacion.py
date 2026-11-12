"""Configuración tributaria de una empresa para emitir facturas SRI."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator


class ConfiguracionFacturacion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ambiente: Literal["1", "2"]
    establecimiento: str = Field(pattern=r"^[0-9]{3}$")
    punto_emision: str = Field(pattern=r"^[0-9]{3}$")
    obligado_contabilidad: StrictBool
    contribuyente_especial: str | None = None
    contribuyente_rimpe: StrictBool

    @field_validator("contribuyente_especial")
    @classmethod
    def validar_contribuyente_especial(cls, valor: str | None) -> str | None:
        if valor is not None:
            valor = valor.strip()
            if not valor or not valor.isdigit() or len(valor) > 13:
                raise ValueError("El número de contribuyente especial no es válido.")
        return valor
