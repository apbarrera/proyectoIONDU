"""Cifrado AES-256-GCM de secretos y lectura del certificado .p12."""

import base64
import subprocess
import sys
from datetime import UTC, datetime, timedelta

import pytest

from app.core import cifrado
from app.core.cifrado import (
    Cifrador,
    DatoCifradoInvalidoError,
    generar_llave_maestra,
    get_cifrador,
    leer_llave_maestra,
)
from app.core.config import get_settings
from app.sri.certificado import CertificadoInvalidoError, cargar_p12
from tests.certificados import CLAVE_P12, crear_p12

LLAVE = leer_llave_maestra(generar_llave_maestra())
P12 = crear_p12()


# ---------- Cifrado ----------
def test_cifra_y_descifra_un_p12():
    c = Cifrador(LLAVE)
    guardado = c.cifrar(P12, "empresa:7:p12")
    assert P12 not in guardado  # en la base no queda el certificado en claro
    assert c.descifrar(guardado, "empresa:7:p12") == P12


def test_cifrar_dos_veces_lo_mismo_da_resultados_distintos():
    c = Cifrador(LLAVE)
    assert c.cifrar(b"clave", "x") != c.cifrar(b"clave", "x")  # nonce nuevo cada vez


def test_un_dato_copiado_a_otra_empresa_no_se_descifra():
    c = Cifrador(LLAVE)
    guardado = c.cifrar(P12, "empresa:7:p12")
    with pytest.raises(DatoCifradoInvalidoError):
        c.descifrar(guardado, "empresa:9:p12")
    with pytest.raises(DatoCifradoInvalidoError):
        c.descifrar(guardado, "empresa:7:p12_clave")  # ni en otro campo de la misma empresa


def test_un_dato_alterado_no_se_descifra():
    c = Cifrador(LLAVE)
    guardado = bytearray(c.cifrar(b"secreto", "x"))
    guardado[-1] ^= 0x01  # se cambia un solo bit
    with pytest.raises(DatoCifradoInvalidoError, match="alterado"):
        c.descifrar(bytes(guardado), "x")


def test_con_otra_llave_no_se_descifra():
    guardado = Cifrador(LLAVE).cifrar(b"secreto", "x")
    otra = Cifrador(leer_llave_maestra(generar_llave_maestra()))
    with pytest.raises(DatoCifradoInvalidoError):
        otra.descifrar(guardado, "x")


@pytest.mark.parametrize("dato", [b"", b"\x02" + b"0" * 40, b"\x01corto"])
def test_formato_o_version_desconocidos(dato):
    with pytest.raises(DatoCifradoInvalidoError, match="Formato"):
        Cifrador(LLAVE).descifrar(dato, "x")


# ---------- Llave maestra ----------
def test_la_llave_generada_tiene_32_bytes():
    assert len(base64.b64decode(generar_llave_maestra())) == 32


@pytest.mark.parametrize(
    ("valor", "error"),
    [
        ("no es base64!", "base64"),
        (base64.b64encode(b"corta").decode(), "32 bytes"),
    ],
)
def test_llave_maestra_invalida(valor, error):
    with pytest.raises(ValueError, match=error):
        leer_llave_maestra(valor)


def test_sin_llave_maestra_configurada_avisa_como_generarla(monkeypatch):
    monkeypatch.setenv("MASTER_ENCRYPTION_KEY", "")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="python -m app.core.cifrado"):
            get_cifrador()
    finally:
        get_settings.cache_clear()


def test_con_llave_maestra_configurada(monkeypatch):
    monkeypatch.setenv("MASTER_ENCRYPTION_KEY", generar_llave_maestra())
    get_settings.cache_clear()
    cifrado._cifrador.cache_clear()
    try:
        c = get_cifrador()
        assert c.descifrar(c.cifrar(b"ok", "x"), "x") == b"ok"
    finally:
        get_settings.cache_clear()
        cifrado._cifrador.cache_clear()


def test_el_comando_genera_una_llave_valida():
    salida = subprocess.run(
        [sys.executable, "-m", "app.core.cifrado"], capture_output=True, text=True, check=True
    )
    assert len(leer_llave_maestra(salida.stdout.strip())) == 32


# ---------- Certificado .p12 ----------
def test_lee_el_titular_y_las_fechas_del_p12():
    cert = cargar_p12(P12, CLAVE_P12)
    assert cert.titular == "CAFETERIA DEMO S.A."
    assert cert.emisor == "AUTORIDAD DE PRUEBA IONDU"
    assert 360 <= cert.dias_para_vencer() <= 365
    assert not cert.vencido() and not cert.por_vencer()


def test_contrasena_incorrecta():
    with pytest.raises(CertificadoInvalidoError, match="contraseña es incorrecta"):
        cargar_p12(P12, "otra-clave")


def test_archivo_que_no_es_un_p12():
    with pytest.raises(CertificadoInvalidoError, match="dañado"):
        cargar_p12(b"esto no es un certificado", CLAVE_P12)


def test_certificado_con_llave_no_rsa():
    with pytest.raises(CertificadoInvalidoError, match="RSA"):
        cargar_p12(crear_p12(llave_ec=True), CLAVE_P12)


def test_avisa_cuando_esta_por_vencer_y_cuando_vencio():
    por_vencer = cargar_p12(crear_p12(dias_validez=20), CLAVE_P12)
    assert por_vencer.por_vencer() and not por_vencer.vencido()

    hace_dos_anios = datetime.now(UTC) - timedelta(days=730)
    vencido = cargar_p12(crear_p12(desde=hace_dos_anios, dias_validez=365), CLAVE_P12)
    assert vencido.vencido() and not vencido.por_vencer()
