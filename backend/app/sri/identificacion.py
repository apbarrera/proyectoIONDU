"""Validación de identificaciones del comprador según el SRI.

Códigos de la ficha técnica de comprobantes electrónicos (tabla "tipo de identificación"):
04 RUC · 05 cédula · 06 pasaporte · 07 consumidor final · 08 identificación del exterior.

Decisión (ver docs/DECISIONES.md): la cédula y el RUC de persona natural se validan
de forma estricta. En el RUC de sociedades y entidades públicas se valida estricta la
estructura, pero si el dígito verificador no cuadra se acepta con una advertencia:
el SRI ha emitido RUC de sociedades que no cumplen el algoritmo clásico, y rechazar
un RUC real impediría facturarle a ese cliente.
"""

import re
from dataclasses import dataclass
from enum import StrEnum


class TipoIdentificacion(StrEnum):
    RUC = "04"
    CEDULA = "05"
    PASAPORTE = "06"
    CONSUMIDOR_FINAL = "07"
    EXTERIOR = "08"


CONSUMIDOR_FINAL = "9999999999999"

_SOLO_DIGITOS = re.compile(r"\d+")
_ALFANUMERICO = re.compile(r"[A-Za-z0-9]{3,20}")


@dataclass(frozen=True)
class Resultado:
    """`valida` indica si se puede usar; `advertencia` es un aviso que no impide usarla."""

    valida: bool
    error: str | None = None
    advertencia: str | None = None


def _provincia_valida(codigo: str) -> bool:
    return 1 <= int(codigo) <= 24 or codigo == "30"


def _modulo11(digitos: str, coeficientes: tuple[int, ...]) -> int | None:
    """Dígito verificador módulo 11 del RUC. None si el resultado es 10 (no existe tal dígito)."""
    total = sum(int(d) * c for d, c in zip(digitos, coeficientes, strict=True))
    resultado = 11 - total % 11
    if resultado == 11:
        return 0
    return None if resultado == 10 else resultado


def validar_cedula(numero: str) -> Resultado:
    if len(numero) != 10 or not _SOLO_DIGITOS.fullmatch(numero):
        return Resultado(False, "La cédula debe tener 10 dígitos.")
    if not _provincia_valida(numero[:2]):
        return Resultado(False, "Los dos primeros dígitos no corresponden a una provincia.")
    if int(numero[2]) > 5:
        return Resultado(False, "El tercer dígito de una cédula debe estar entre 0 y 5.")

    # Módulo 10: coeficientes 2,1,2,1,...; si un producto pasa de 9 se le resta 9.
    total = 0
    for digito, coeficiente in zip(numero[:9], (2, 1, 2, 1, 2, 1, 2, 1, 2), strict=True):
        producto = int(digito) * coeficiente
        total += producto - 9 if producto > 9 else producto
    verificador = (10 - total % 10) % 10
    if verificador != int(numero[9]):
        return Resultado(False, "El dígito verificador de la cédula no es correcto.")
    return Resultado(True)


def validar_ruc(numero: str) -> Resultado:
    if len(numero) != 13 or not _SOLO_DIGITOS.fullmatch(numero):
        return Resultado(False, "El RUC debe tener 13 dígitos.")
    if numero == CONSUMIDOR_FINAL:
        return Resultado(False, "Para consumidor final usa el tipo de identificación 07.")
    if not _provincia_valida(numero[:2]):
        return Resultado(False, "Los dos primeros dígitos no corresponden a una provincia.")

    tercero = int(numero[2])
    if tercero <= 5:  # persona natural: cédula + establecimiento
        cedula = validar_cedula(numero[:10])
        if not cedula.valida:
            return Resultado(False, f"RUC de persona natural con cédula inválida: {cedula.error}")
        if numero[10:] == "000":
            return Resultado(False, "Los tres últimos dígitos (establecimiento) no pueden ser 000.")
        return Resultado(True)

    if tercero == 9:  # sociedad privada o extranjera
        if numero[10:] == "000":
            return Resultado(False, "Los tres últimos dígitos (establecimiento) no pueden ser 000.")
        verificador = _modulo11(numero[:9], (4, 3, 2, 7, 6, 5, 4, 3, 2))
        cuadra = verificador == int(numero[9])
    elif tercero == 6:  # entidad pública
        if numero[9:] == "0000":
            return Resultado(
                False, "Los cuatro últimos dígitos (establecimiento) no pueden ser 0000."
            )
        verificador = _modulo11(numero[:8], (3, 2, 7, 6, 5, 4, 3, 2))
        cuadra = verificador == int(numero[8])
    else:
        return Resultado(
            False, "El tercer dígito del RUC no corresponde a ningún tipo de contribuyente."
        )

    if cuadra:
        return Resultado(True)
    return Resultado(
        True,
        advertencia="El dígito verificador del RUC no cumple el algoritmo clásico; "
        "confirma el número con el cliente.",
    )


def validar_identificacion(tipo: TipoIdentificacion | str, numero: str) -> Resultado:
    """Valida el número según su tipo. Quita los espacios al inicio y al final."""
    numero = numero.strip()
    try:
        tipo = TipoIdentificacion(tipo)
    except ValueError:
        return Resultado(False, "Tipo de identificación no reconocido.")

    match tipo:
        case TipoIdentificacion.CEDULA:
            return validar_cedula(numero)
        case TipoIdentificacion.RUC:
            return validar_ruc(numero)
        case TipoIdentificacion.CONSUMIDOR_FINAL:
            if numero != CONSUMIDOR_FINAL:
                return Resultado(False, f"Para consumidor final el número es {CONSUMIDOR_FINAL}.")
            return Resultado(True)
        case TipoIdentificacion.PASAPORTE | TipoIdentificacion.EXTERIOR:
            if not _ALFANUMERICO.fullmatch(numero):
                return Resultado(False, "Debe tener entre 3 y 20 letras o números, sin espacios.")
            return Resultado(True)
