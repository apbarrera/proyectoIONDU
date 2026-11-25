"""Piezas comunes de los repositorios."""

from sqlalchemy import ColumnElement, or_
from sqlalchemy.orm import InstrumentedAttribute


def contiene_texto(texto: str, *columnas: InstrumentedAttribute) -> ColumnElement[bool]:
    """Condición "alguna columna contiene el texto", sin distinguir mayúsculas.

    Escapa % y _ para que se busquen como texto y no como comodines de LIKE.
    """
    escapado = texto.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
    patron = f"%{escapado}%"
    return or_(*(columna.ilike(patron, escape="\\") for columna in columnas))
