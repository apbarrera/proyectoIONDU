"""Clave de acceso de 49 dígitos (módulo 11)."""

import re
from datetime import date

import pytest

from app.sri.clave_acceso import (
    Ambiente,
    TipoComprobante,
    digito_verificador,
    generar_clave_acceso,
    hoy_en_ecuador,
    leer_clave_acceso,
)

# Calculada aparte: los 48 dígitos por 2,3,4,5,6,7 (de derecha a izquierda) suman 478;
# 478 mod 11 = 5; 11 - 5 = 6 -> dígito verificador 6.
CLAVE_EJEMPLO = "2510202601179001093700110010010000001231234567816"

DATOS = {
    "ruc_emisor": "1790010937001",
    "establecimiento": "001",
    "punto_emision": "001",
    "secuencial": 123,
    "ambiente": Ambiente.PRUEBAS,
}


def test_genera_la_clave_esperada():
    clave = generar_clave_acceso(
        **DATOS, fecha_emision=date(2026, 10, 25), codigo_numerico="12345678"
    )
    assert clave == CLAVE_EJEMPLO


def test_casos_especiales_del_modulo_11():
    assert digito_verificador("0" * 48) == 0  # 11 - 0 = 11 -> 0
    assert digito_verificador("0" * 47 + "6") == 1  # 6*2 = 12; 11 - 1 = 10 -> 1


def test_leer_devuelve_las_partes():
    partes = leer_clave_acceso(CLAVE_EJEMPLO)
    assert partes.fecha_emision == date(2026, 10, 25)
    assert partes.tipo_comprobante == TipoComprobante.FACTURA
    assert partes.ruc_emisor == "1790010937001"
    assert partes.ambiente == Ambiente.PRUEBAS
    assert (partes.establecimiento, partes.punto_emision) == ("001", "001")
    assert partes.secuencial == 123
    assert partes.codigo_numerico == "12345678"
    assert partes.tipo_emision == "1"


def test_sin_codigo_numerico_genera_uno_al_azar_de_8_digitos():
    claves = {generar_clave_acceso(**DATOS) for _ in range(5)}
    assert len(claves) > 1  # no siempre la misma
    for clave in claves:
        assert re.fullmatch(r"\d{49}", clave)
        leer_clave_acceso(clave)  # y todas son válidas


def test_sin_fecha_usa_el_dia_de_ecuador():
    clave = generar_clave_acceso(**DATOS)
    assert clave[:8] == f"{hoy_en_ecuador():%d%m%Y}"


@pytest.mark.parametrize(
    ("clave", "error"),
    [
        (CLAVE_EJEMPLO[:-1], "49 dígitos"),
        (CLAVE_EJEMPLO[:-1] + "7", "dígito verificador"),
        ("3213" + CLAVE_EJEMPLO[4:-1] + "0", None),  # fecha 32/13: inválida
    ],
)
def test_leer_rechaza_claves_invalidas(clave, error):
    if error is None:  # recalcula el verificador para que solo falle la fecha
        clave = clave[:48] + str(digito_verificador(clave[:48]))
        error = "fecha"
    with pytest.raises(ValueError, match=error):
        leer_clave_acceso(clave)


@pytest.mark.parametrize(
    ("cambio", "error"),
    [
        ({"ruc_emisor": "1790010937000"}, "RUC del emisor"),
        ({"establecimiento": "01"}, "3 dígitos"),
        ({"secuencial": 0}, "secuencial"),
        ({"secuencial": 1_000_000_000}, "secuencial"),
        ({"codigo_numerico": "123"}, "8 dígitos"),
    ],
)
def test_generar_rechaza_datos_invalidos(cambio, error):
    with pytest.raises(ValueError, match=error):
        generar_clave_acceso(**(DATOS | cambio))
