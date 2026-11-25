"""Validación de identificaciones del SRI.

Las cédulas son inventadas (verificador calculado a mano, no son personas reales).
Los RUC de sociedades y entidades públicas son públicos (aparecen en sus facturas).
"""

import pytest

from app.sri.identificacion import (
    CONSUMIDOR_FINAL,
    TipoIdentificacion,
    validar_cedula,
    validar_identificacion,
    validar_ruc,
)


# ---------- Cédula ----------
@pytest.mark.parametrize("cedula", ["1710000009", "0102030400", "3010000002"])
def test_cedulas_validas(cedula):
    assert validar_cedula(cedula).valida


@pytest.mark.parametrize(
    ("cedula", "error"),
    [
        ("171000000", "La cédula debe tener 10 dígitos."),
        ("17100000A9", "La cédula debe tener 10 dígitos."),
        ("2510000009", "Los dos primeros dígitos no corresponden a una provincia."),
        ("0010000009", "Los dos primeros dígitos no corresponden a una provincia."),
        ("1760000009", "El tercer dígito de una cédula debe estar entre 0 y 5."),
        ("1710000008", "El dígito verificador de la cédula no es correcto."),
    ],
)
def test_cedulas_invalidas_explican_el_motivo(cedula, error):
    resultado = validar_cedula(cedula)
    assert not resultado.valida
    assert resultado.error == error


# ---------- RUC ----------
@pytest.mark.parametrize(
    "ruc",
    [
        "1710000009001",  # persona natural (cédula inventada + establecimiento 001)
        "1790010937001",  # sociedad: Banco Pichincha
        "1790016919001",  # sociedad: Corporación Favorita
        "1760013210001",  # entidad pública: SRI
    ],
)
def test_ruc_validos_sin_advertencia(ruc):
    resultado = validar_ruc(ruc)
    assert resultado.valida
    assert resultado.advertencia is None


def test_ruc_de_sociedad_con_verificador_distinto_se_acepta_con_advertencia():
    resultado = validar_ruc("1790010938001")  # Banco Pichincha con el décimo dígito cambiado
    assert resultado.valida
    assert "confirma el número" in resultado.advertencia


def test_ruc_publico_con_verificador_distinto_se_acepta_con_advertencia():
    resultado = validar_ruc("1760013220001")  # SRI con el noveno dígito cambiado
    assert resultado.valida
    assert resultado.advertencia is not None


@pytest.mark.parametrize(
    ("ruc", "parte_del_error"),
    [
        ("17900109370", "13 dígitos"),
        ("1710000008001", "cédula inválida"),  # persona natural: el verificador es estricto
        ("1710000009000", "000"),
        ("1790010937000", "000"),
        ("1760013210000", "0000"),
        ("1770000000001", "tercer dígito"),
        ("2590010937001", "provincia"),
        (CONSUMIDOR_FINAL, "tipo de identificación 07"),
    ],
)
def test_ruc_invalidos_explican_el_motivo(ruc, parte_del_error):
    resultado = validar_ruc(ruc)
    assert not resultado.valida
    assert parte_del_error in resultado.error


# ---------- Por tipo ----------
def test_consumidor_final_solo_acepta_trece_nueves():
    assert validar_identificacion("07", "9999999999999").valida
    assert not validar_identificacion("07", "9999999999").valida  # 10 nueves: lo rechaza el SRI


def test_valida_segun_el_tipo_y_quita_espacios():
    assert validar_identificacion(TipoIdentificacion.CEDULA, " 1710000009 ").valida
    assert validar_identificacion("04", "1790010937001").valida
    assert validar_identificacion("06", "AB123456").valida
    assert not validar_identificacion("06", "AB 123").valida
    assert not validar_identificacion("05", "1790010937001").valida  # un RUC no es una cédula


def test_tipo_desconocido():
    resultado = validar_identificacion("99", "1710000009")
    assert not resultado.valida
    assert resultado.error == "Tipo de identificación no reconocido."
