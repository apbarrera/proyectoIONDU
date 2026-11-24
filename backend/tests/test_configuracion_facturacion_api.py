from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import configuracion_facturacion as api
from app.api.deps import Contexto, get_contexto
from app.core.errors import UnprocessableError
from app.db.session import get_db
from app.main import app
from app.models.rol import ADMINISTRADOR, OPERATIVO
from app.schemas.configuracion_facturacion import ConfiguracionFacturacion
from app.services.configuracion_facturacion import (
    ConfiguracionFacturacionService,
)


def _configuracion():
    return ConfiguracionFacturacion(
        ambiente="1",
        establecimiento="001",
        punto_emision="001",
        obligado_contabilidad=True,
        contribuyente_especial=None,
        contribuyente_rimpe=False,
        direccion_establecimiento="Av. Amazonas 123, Quito",
    )


def _payload():
    return {
        "ambiente": "1",
        "establecimiento": "001",
        "puntoEmision": "001",
        "obligadoContabilidad": True,
        "contribuyenteEspecial": None,
        "contribuyenteRimpe": False,
        "direccionEstablecimiento": "Av. Amazonas 123, Quito",
    }


def _contexto(rol=ADMINISTRADOR, empresa_id=7):
    return Contexto(
        empresa_id=empresa_id,
        rol=rol,
        usuario=SimpleNamespace(id=uuid4()),
    )


def _preparar_api(monkeypatch, contexto, servicio):
    app.dependency_overrides[get_contexto] = lambda: contexto
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(api, "ConfiguracionFacturacionService", servicio)


def _limpiar_api():
    app.dependency_overrides.pop(get_contexto, None)
    app.dependency_overrides.pop(get_db, None)


def test_api_get_devuelve_configuracion_y_usa_empresa_autenticada(monkeypatch):
    llamadas = []

    class ServicioFalso:
        def __init__(self, db, empresa_id):
            llamadas.append({"empresa_id": empresa_id})

        def obtener(self):
            return _configuracion()

    _preparar_api(monkeypatch, _contexto(empresa_id=17), ServicioFalso)

    try:
        respuesta = TestClient(app).get(
            "/api/company/billing-config",
            headers={"X-Empresa-Id": "999"},
        )
    finally:
        _limpiar_api()

    assert respuesta.status_code == 200
    assert llamadas == [{"empresa_id": 17}]

    datos = respuesta.json()
    assert datos["ambiente"] == "1"
    assert datos["establecimiento"] == "001"
    assert datos["puntoEmision"] == "001"
    assert datos["direccionEstablecimiento"] == "Av. Amazonas 123, Quito"


def test_api_get_devuelve_null_si_no_hay_configuracion(monkeypatch):
    class ServicioFalso:
        def __init__(self, db, empresa_id):
            pass

        def obtener(self):
            return None

    _preparar_api(monkeypatch, _contexto(), ServicioFalso)

    try:
        respuesta = TestClient(app).get("/api/company/billing-config")
    finally:
        _limpiar_api()

    assert respuesta.status_code == 200
    assert respuesta.json() is None


def test_api_put_actualiza_configuracion_en_empresa_autenticada(monkeypatch):
    llamadas = []

    class ServicioFalso:
        def __init__(self, db, empresa_id):
            llamadas.append({"empresa_id": empresa_id})

        def actualizar(self, configuracion):
            llamadas[-1]["configuracion"] = configuracion
            return configuracion

    _preparar_api(monkeypatch, _contexto(empresa_id=23), ServicioFalso)

    try:
        respuesta = TestClient(app).put(
            "/api/company/billing-config",
            json=_payload(),
            headers={"X-Empresa-Id": "999"},
        )
    finally:
        _limpiar_api()

    assert respuesta.status_code == 200
    assert len(llamadas) == 1
    assert llamadas[0]["empresa_id"] == 23
    assert llamadas[0]["configuracion"].direccion_establecimiento == ("Av. Amazonas 123, Quito")
    assert respuesta.json()["puntoEmision"] == "001"


def test_api_rechaza_usuario_operativo(monkeypatch):
    def servicio_no_debe_ejecutarse(*args, **kwargs):
        raise AssertionError("Un usuario operativo no debe acceder a esta sección.")

    _preparar_api(
        monkeypatch,
        _contexto(rol=OPERATIVO),
        servicio_no_debe_ejecutarse,
    )

    try:
        cliente = TestClient(app)
        respuesta_get = cliente.get("/api/company/billing-config")
        respuesta_put = cliente.put(
            "/api/company/billing-config",
            json=_payload(),
        )
    finally:
        _limpiar_api()

    assert respuesta_get.status_code == 403
    assert respuesta_put.status_code == 403


def test_api_rechaza_empresa_id_en_el_body(monkeypatch):
    def servicio_no_debe_ejecutarse(*args, **kwargs):
        raise AssertionError("No debe ejecutarse con campos adicionales.")

    _preparar_api(monkeypatch, _contexto(), servicio_no_debe_ejecutarse)

    payload = _payload()
    payload["empresaId"] = 999

    try:
        respuesta = TestClient(app).put(
            "/api/company/billing-config",
            json=payload,
        )
    finally:
        _limpiar_api()

    assert respuesta.status_code == 422


class FakeDB:
    def __init__(self, empresa):
        self.empresa = empresa
        self.commits = 0
        self.rollbacks = 0
        self.fallar_commit = False

    def scalar(self, sentencia):
        return self.empresa

    def commit(self):
        self.commits += 1
        if self.fallar_commit:
            raise RuntimeError("Error simulado de persistencia.")

    def rollback(self):
        self.rollbacks += 1


def _empresa(datos):
    return SimpleNamespace(
        id_empresa=7,
        datos_facturacion_electronica=datos,
    )


def test_servicio_get_conserva_compatibilidad_con_claves_jsonb_ajenas():
    empresa = _empresa(
        {
            **_payload(),
            "clave_otra_funcionalidad": "conservar",
        }
    )
    db = FakeDB(empresa)

    resultado = ConfiguracionFacturacionService(db, 7).obtener()

    assert resultado.direccion_establecimiento == "Av. Amazonas 123, Quito"
    assert db.commits == 0
    assert empresa.datos_facturacion_electronica["clave_otra_funcionalidad"] == "conservar"


def test_servicio_put_preserva_claves_jsonb_ajenas():
    empresa = _empresa(
        {
            "clave_otra_funcionalidad": {"activo": True},
        }
    )
    db = FakeDB(empresa)

    resultado = ConfiguracionFacturacionService(db, 7).actualizar(_configuracion())

    assert resultado.direccion_establecimiento == "Av. Amazonas 123, Quito"
    assert empresa.datos_facturacion_electronica["clave_otra_funcionalidad"] == {"activo": True}
    assert empresa.datos_facturacion_electronica["punto_emision"] == "001"
    assert db.commits == 1
    assert db.rollbacks == 0


def test_servicio_rechaza_jsonb_que_no_es_un_objeto():
    empresa = _empresa(["dato", "invalido"])
    db = FakeDB(empresa)

    with pytest.raises(UnprocessableError):
        ConfiguracionFacturacionService(db, 7).obtener()

    with pytest.raises(UnprocessableError):
        ConfiguracionFacturacionService(db, 7).actualizar(_configuracion())

    assert db.commits == 0


def test_servicio_rechaza_configuracion_almacenada_invalida():
    empresa = _empresa({"ambiente": "ambiente-invalido"})
    db = FakeDB(empresa)

    with pytest.raises(UnprocessableError):
        ConfiguracionFacturacionService(db, 7).obtener()

    assert db.commits == 0


def test_servicio_revierte_si_falla_el_commit():
    empresa = _empresa(None)
    db = FakeDB(empresa)
    db.fallar_commit = True

    with pytest.raises(RuntimeError, match="Error simulado"):
        ConfiguracionFacturacionService(db, 7).actualizar(_configuracion())

    assert db.commits == 1
    assert db.rollbacks == 1
