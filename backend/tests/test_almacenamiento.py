"""Pruebas unitarias del almacenamiento privado de archivos RIDE (API S3, sin red)."""

import io
from types import SimpleNamespace

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError
from pydantic import SecretStr

from app.core.errors import NotFoundError, ServiceUnavailableError
from app.services.almacenamiento import (
    AlmacenamientoRideService,
    crear_almacenamiento,
    crear_cliente_s3,
)


def _error_s3(codigo: str) -> ClientError:
    return ClientError({"Error": {"Code": codigo, "Message": "simulado"}}, "operacion")


class S3Falso:
    """Imita las llamadas de boto3 que usa el servicio."""

    def __init__(self):
        self.objetos: dict[tuple[str, str], tuple[bytes, str]] = {}
        self.buckets: set[str] = set()
        self.error: Exception | None = None

    def put_object(self, Bucket, Key, Body, ContentType):  # noqa: N803 (nombres de boto3)
        if self.error:
            raise self.error
        self.objetos[(Bucket, Key)] = (Body, ContentType)

    def get_object(self, Bucket, Key):  # noqa: N803
        if self.error:
            raise self.error
        if (Bucket, Key) not in self.objetos:
            raise _error_s3("NoSuchKey")
        return {"Body": io.BytesIO(self.objetos[(Bucket, Key)][0])}

    def head_bucket(self, Bucket):  # noqa: N803
        if Bucket not in self.buckets:
            raise _error_s3("404")

    def create_bucket(self, Bucket):  # noqa: N803
        self.buckets.add(Bucket)


RUTA = "empresas/12/facturas/34/ride.pdf"
PDF = b"%PDF-1.4 contenido de prueba"


@pytest.fixture
def cliente():
    return S3Falso()


@pytest.fixture
def servicio(cliente):
    return AlmacenamientoRideService(cliente)


def test_construir_ruta_aislada_por_empresa_y_factura():
    assert AlmacenamientoRideService.construir_ruta(12, 34) == RUTA


@pytest.mark.parametrize(
    ("empresa_id", "factura_id"),
    [(0, 1), (1, 0), (-1, 2), (2, -1)],
)
def test_construir_ruta_rechaza_identificadores_no_positivos(empresa_id, factura_id):
    with pytest.raises(ValueError):
        AlmacenamientoRideService.construir_ruta(empresa_id, factura_id)


def test_guardar_sube_el_pdf_al_bucket_con_su_tipo(servicio, cliente):
    ruta = servicio.guardar(12, 34, PDF)

    assert ruta == RUTA
    assert cliente.objetos[("rides", RUTA)] == (PDF, "application/pdf")


def test_guardar_reemplaza_el_ride_existente(servicio, cliente):
    servicio.guardar(12, 34, b"%PDF-1.4 version 1")
    servicio.guardar(12, 34, PDF)
    assert cliente.objetos[("rides", RUTA)][0] == PDF


@pytest.mark.parametrize("contenido", [b"", None, "texto"])
def test_guardar_rechaza_contenido_vacio_o_no_binario(servicio, contenido):
    with pytest.raises(ValueError):
        servicio.guardar(12, 34, contenido)


def test_descargar_devuelve_el_pdf_guardado(servicio):
    servicio.guardar(12, 34, PDF)
    assert servicio.descargar(RUTA) == PDF


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


def test_descargar_un_ride_que_no_existe_es_404(servicio):
    with pytest.raises(NotFoundError):
        servicio.descargar(RUTA)


def test_descargar_un_archivo_vacio_es_404(servicio, cliente):
    cliente.objetos[("rides", RUTA)] = (b"", "application/pdf")
    with pytest.raises(NotFoundError):
        servicio.descargar(RUTA)


@pytest.mark.parametrize(
    "error",
    [_error_s3("AccessDenied"), EndpointConnectionError(endpoint_url="http://storage:8333")],
)
def test_errores_del_almacenamiento_se_traducen_a_servicio_no_disponible(servicio, cliente, error):
    cliente.error = error

    with pytest.raises(ServiceUnavailableError) as al_subir:
        servicio.guardar(12, 34, PDF)
    with pytest.raises(ServiceUnavailableError) as al_bajar:
        servicio.descargar(RUTA)

    assert al_subir.value.code == al_bajar.value.code == "RIDE_STORAGE_UNAVAILABLE"


def test_asegurar_bucket_lo_crea_solo_si_falta(servicio, cliente):
    servicio.asegurar_bucket()
    assert cliente.buckets == {"rides"}
    servicio.asegurar_bucket()  # ya existe: no falla
    assert cliente.buckets == {"rides"}


def _settings(**cambios):
    base = {
        "storage_endpoint_url": "http://storage:8333",
        "storage_region": "us-east-1",
        "storage_access_key_id": "clave",
        "storage_secret_access_key": SecretStr("secreto"),
        "storage_bucket": "rides",
    }
    return SimpleNamespace(**(base | cambios))


@pytest.mark.parametrize(
    "faltante", ["storage_endpoint_url", "storage_access_key_id", "storage_secret_access_key"]
)
def test_sin_configuracion_completa_no_hay_almacenamiento(faltante):
    settings = _settings(**{faltante: None})
    assert crear_cliente_s3(settings) is None
    assert crear_almacenamiento(settings) is None


def test_con_configuracion_crea_un_cliente_s3_con_rutas_por_bucket():
    cliente = crear_cliente_s3(_settings())
    assert cliente.meta.endpoint_url == "http://storage:8333"
    assert cliente.meta.config.s3["addressing_style"] == "path"


def test_asegurar_bucket_tolera_que_otro_proceso_lo_haya_creado(servicio, cliente, caplog):
    def ya_creado(Bucket):  # noqa: N803
        raise _error_s3("BucketAlreadyOwnedByYou")

    cliente.create_bucket = ya_creado
    servicio.asegurar_bucket()
    assert "No se pudo crear" not in caplog.text
