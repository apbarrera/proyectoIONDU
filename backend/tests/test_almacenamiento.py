"""Pruebas unitarias del almacenamiento privado de archivos RIDE."""

import pytest

from app.core.errors import NotFoundError, ServiceUnavailableError
from app.services.almacenamiento import AlmacenamientoRideService


class StorageFalso:
    def __init__(self):
        self.ruta = None
        self.contenido = None
        self.opciones = None
        self.error = None
        self.contenido_descarga = b"%PDF-1.4 prueba"

    def from_(self, bucket):
        self.bucket = bucket
        return self

    def upload(self, ruta, contenido, opciones):
        if self.error:
            raise self.error
        self.ruta = ruta
        self.contenido = contenido
        self.opciones = opciones

    def download(self, ruta):
        if self.error:
            raise self.error
        self.ruta = ruta
        return self.contenido_descarga


class ClienteFalso:
    def __init__(self):
        self.storage = StorageFalso()


@pytest.fixture
def cliente():
    return ClienteFalso()


@pytest.fixture
def servicio(cliente):
    return AlmacenamientoRideService(cliente)


def test_construir_ruta_aislada_por_empresa_y_factura():
    ruta = AlmacenamientoRideService.construir_ruta(12, 34)

    assert ruta == "empresas/12/facturas/34/ride.pdf"


@pytest.mark.parametrize(
    ("empresa_id", "factura_id"),
    [(0, 1), (1, 0), (-1, 2), (2, -1)],
)
def test_construir_ruta_rechaza_identificadores_no_positivos(empresa_id, factura_id):
    with pytest.raises(ValueError):
        AlmacenamientoRideService.construir_ruta(empresa_id, factura_id)


def test_guardar_subida_pdf_con_tipo_y_upsert(servicio, cliente):
    pdf = b"%PDF-1.4 contenido de prueba"

    ruta = servicio.guardar(12, 34, pdf)

    assert ruta == "empresas/12/facturas/34/ride.pdf"
    assert cliente.storage.bucket == "rides"
    assert cliente.storage.ruta == ruta
    assert cliente.storage.contenido == pdf
    assert cliente.storage.opciones["content-type"] == "application/pdf"
    assert cliente.storage.opciones["upsert"] == "true"


@pytest.mark.parametrize("contenido", [b"", None, "texto"])
def test_guardar_rechaza_contenido_vacio_o_no_binario(servicio, contenido):
    with pytest.raises(ValueError):
        servicio.guardar(12, 34, contenido)


def test_descargar_devuelve_contenido_pdf(servicio, cliente):
    pdf = b"%PDF-1.4 contenido de prueba"
    cliente.storage.contenido_descarga = pdf

    resultado = servicio.descargar("empresas/12/facturas/34/ride.pdf")

    assert resultado == pdf
    assert cliente.storage.bucket == "rides"


@pytest.mark.parametrize(
    "ruta",
    [
        "",
        "../facturas/34/ride.pdf",
        "/empresas/12/facturas/34/ride.pdf",
        "empresas/12/../../ride.pdf",
        "otra-ruta/facturas/34/ride.pdf",
        "empresas/12/facturas/34/otro.pdf",
    ],
)
def test_descargar_rechaza_rutas_invalidas(servicio, ruta):
    with pytest.raises(NotFoundError):
        servicio.descargar(ruta)


def test_descargar_rechaza_archivo_no_disponible(servicio, cliente):
    cliente.storage.contenido_descarga = b""

    with pytest.raises(NotFoundError):
        servicio.descargar("empresas/12/facturas/34/ride.pdf")


def test_error_de_subida_se_traduce_a_servicio_no_disponible(servicio, cliente):
    cliente.storage.error = RuntimeError("error simulado")

    with pytest.raises(ServiceUnavailableError) as resultado:
        servicio.guardar(12, 34, b"%PDF-1.4 prueba")

    assert resultado.value.code == "RIDE_STORAGE_UNAVAILABLE"


def test_error_de_descarga_se_traduce_a_servicio_no_disponible(servicio, cliente):
    cliente.storage.error = RuntimeError("error simulado")

    with pytest.raises(ServiceUnavailableError) as resultado:
        servicio.descargar("empresas/12/facturas/34/ride.pdf")

    assert resultado.value.code == "RIDE_STORAGE_UNAVAILABLE"
