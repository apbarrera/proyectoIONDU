"""Pruebas unitarias del servicio de certificados de empresa."""

import base64
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.errors import NotFoundError, UnprocessableError
from app.services import certificado_empresa as servicio
from app.sri.certificado import CertificadoInvalidoError
from tests.certificados import CLAVE_P12, crear_p12


@pytest.fixture
def db():
    return Mock()


@pytest.fixture
def empresa():
    return SimpleNamespace(
        id_empresa=1,
        certificado_p12_cifrado=None,
        certificado_password_cifrada=None,
        certificado_fecha_vencimiento=None,
    )


@pytest.fixture
def cifrador():
    from app.core.cifrado import Cifrador, generar_llave_maestra, leer_llave_maestra

    return Cifrador(leer_llave_maestra(generar_llave_maestra()))


@pytest.fixture
def service(db, empresa, cifrador, monkeypatch):
    db.scalar.return_value = empresa
    monkeypatch.setattr(servicio, "get_cifrador", lambda: cifrador)
    return servicio.CertificadoEmpresaService(db, empresa.id_empresa)


def test_rechaza_contenido_vacio(service):
    with pytest.raises(UnprocessableError, match="seleccionar"):
        service.guardar(b"", CLAVE_P12)


def test_rechaza_archivo_mayor_al_limite(service):
    contenido = b"x" * (servicio.TAMANO_MAXIMO_P12 + 1)

    with pytest.raises(UnprocessableError, match="5 MiB"):
        service.guardar(contenido, CLAVE_P12)


def test_rechaza_contrasena_vacia(service):
    with pytest.raises(UnprocessableError, match="contraseña"):
        service.guardar(crear_p12(), "   ")


def test_rechaza_certificado_invalido(service, monkeypatch):
    def certificado_invalido(*args, **kwargs):
        raise CertificadoInvalidoError("archivo inválido")

    monkeypatch.setattr(servicio, "cargar_p12", certificado_invalido)

    with pytest.raises(UnprocessableError, match="validar el certificado"):
        service.guardar(b"archivo", CLAVE_P12)


def test_rechaza_certificado_vencido(service, monkeypatch):
    vencimiento = datetime.now(UTC) - timedelta(days=1)
    certificado = SimpleNamespace(
        vence=vencimiento,
        vencido=lambda: True,
    )
    monkeypatch.setattr(servicio, "cargar_p12", lambda *args: certificado)

    with pytest.raises(UnprocessableError, match="vencido"):
        service.guardar(b"contenido", CLAVE_P12)


def test_empresa_inexistente(db, cifrador, monkeypatch):
    db.scalar.return_value = None
    monkeypatch.setattr(servicio, "get_cifrador", lambda: cifrador)
    service = servicio.CertificadoEmpresaService(db, 999)

    with pytest.raises(NotFoundError, match="empresa"):
        service.guardar(crear_p12(), CLAVE_P12)


def test_guarda_certificado_y_contrasena_cifrados(service, db, empresa, cifrador):
    contenido = crear_p12()

    resultado = service.guardar(contenido, CLAVE_P12)

    assert resultado["mensaje"] == "Certificado electrónico guardado correctamente."
    assert empresa.certificado_p12_cifrado is not None
    assert empresa.certificado_password_cifrada is not None

    guardado_p12 = base64.b64decode(empresa.certificado_p12_cifrado)
    guardada_clave = base64.b64decode(empresa.certificado_password_cifrada)

    assert contenido not in guardado_p12
    assert CLAVE_P12.encode() not in guardada_clave

    # Comprobar que cada valor se puede descifrar solo con su contexto.
    assert cifrador.descifrar(guardado_p12, "empresa:1:p12") == contenido

    assert cifrador.descifrar(guardada_clave, "empresa:1:p12_password") == CLAVE_P12.encode("utf-8")

    # El servicio debe confirmar la transacción.
    db.commit.assert_called_once()
