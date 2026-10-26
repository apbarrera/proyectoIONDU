"""Clave de acceso de 49 dígitos de los comprobantes electrónicos (ficha técnica del SRI).

ddmmaaaa | tipo | RUC emisor | ambiente | serie | secuencial | código | emisión | DV
   8        2        13          1         6        9           8        1       1
"""

import re
import secrets
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from zoneinfo import ZoneInfo

from app.core.config import TIMEZONE
from app.sri.identificacion import validar_ruc


class TipoComprobante(StrEnum):
    FACTURA = "01"
    LIQUIDACION_COMPRA = "03"
    NOTA_CREDITO = "04"
    NOTA_DEBITO = "05"
    GUIA_REMISION = "06"
    RETENCION = "07"


class Ambiente(StrEnum):
    PRUEBAS = "1"
    PRODUCCION = "2"


TIPO_EMISION_NORMAL = "1"

_CLAVE = re.compile(r"\d{49}")
_TRES_DIGITOS = re.compile(r"\d{3}")
_OCHO_DIGITOS = re.compile(r"\d{8}")


def digito_verificador(digitos: str) -> int:
    """Módulo 11 de la clave: de derecha a izquierda por 2,3,4,5,6,7,2,3,...
    Si el resultado es 11 el dígito es 0; si es 10, es 1."""
    total = sum(int(d) * (2 + i % 6) for i, d in enumerate(reversed(digitos)))
    resultado = 11 - total % 11
    return {11: 0, 10: 1}.get(resultado, resultado)


def hoy_en_ecuador() -> date:
    """Fecha de emisión: la del calendario de Ecuador, no la del servidor (UTC)."""
    return datetime.now(ZoneInfo(TIMEZONE)).date()


def generar_clave_acceso(
    *,
    ruc_emisor: str,
    establecimiento: str,
    punto_emision: str,
    secuencial: int,
    ambiente: Ambiente,
    tipo_comprobante: TipoComprobante = TipoComprobante.FACTURA,
    fecha_emision: date | None = None,
    codigo_numerico: str | None = None,
) -> str:
    """Arma la clave de 49 dígitos. Lanza ValueError si algún dato no tiene el formato."""
    if not validar_ruc(ruc_emisor).valida:
        raise ValueError("El RUC del emisor no es válido.")
    if not (_TRES_DIGITOS.fullmatch(establecimiento) and _TRES_DIGITOS.fullmatch(punto_emision)):
        raise ValueError("El establecimiento y el punto de emisión deben tener 3 dígitos.")
    if not 1 <= secuencial <= 999_999_999:
        raise ValueError("El secuencial debe estar entre 1 y 999999999.")
    if codigo_numerico is None:
        codigo_numerico = f"{secrets.randbelow(10**8):08d}"  # al azar y no predecible
    elif not _OCHO_DIGITOS.fullmatch(codigo_numerico):
        raise ValueError("El código numérico debe tener 8 dígitos.")

    fecha = fecha_emision or hoy_en_ecuador()
    sin_verificador = (
        f"{fecha:%d%m%Y}{TipoComprobante(tipo_comprobante)}{ruc_emisor}{Ambiente(ambiente)}"
        f"{establecimiento}{punto_emision}{secuencial:09d}{codigo_numerico}{TIPO_EMISION_NORMAL}"
    )
    return sin_verificador + str(digito_verificador(sin_verificador))


@dataclass(frozen=True)
class ClaveAcceso:
    """Partes de una clave de acceso ya validada."""

    fecha_emision: date
    tipo_comprobante: str
    ruc_emisor: str
    ambiente: str
    establecimiento: str
    punto_emision: str
    secuencial: int
    codigo_numerico: str
    tipo_emision: str


def leer_clave_acceso(clave: str) -> ClaveAcceso:
    """Valida la clave (largo, fecha y dígito verificador) y devuelve sus partes."""
    if not _CLAVE.fullmatch(clave):
        raise ValueError("La clave de acceso debe tener 49 dígitos.")
    if digito_verificador(clave[:48]) != int(clave[48]):
        raise ValueError("El dígito verificador de la clave de acceso no es correcto.")
    try:
        fecha = datetime.strptime(clave[:8], "%d%m%Y").date()
    except ValueError:
        raise ValueError("La fecha de la clave de acceso no es válida.") from None
    return ClaveAcceso(
        fecha_emision=fecha,
        tipo_comprobante=clave[8:10],
        ruc_emisor=clave[10:23],
        ambiente=clave[23],
        establecimiento=clave[24:27],
        punto_emision=clave[27:30],
        secuencial=int(clave[30:39]),
        codigo_numerico=clave[39:47],
        tipo_emision=clave[47],
    )
