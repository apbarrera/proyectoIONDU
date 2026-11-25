from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import facturas as facturas_api
from app.api.deps import Contexto, get_contexto
from app.main import app
from app.models.rol import OPERATIVO


def _factura_falsa():
    return SimpleNamespace(
        id_factura=501,
        id_venta=101,
        numero_comprobante="001-001-000000001",
        clave_acceso="1234567890123456789012345678901234567890123456789",
        estado_autorizacion="autorizada",
        numero_autorizacion="1234567890",
        fecha_autorizacion=datetime(2026, 11, 11, 20, 0, tzinfo=UTC),
        mensajes_sri=[
            {
                "identificador": "70",
                "mensaje": "Comprobante autorizado",
                "informacion_adicional": None,
                "tipo": "INFORMATIVO",
            }
        ],
        fecha_emision=datetime(2026, 11, 11, 19, 55, tzinfo=UTC),
        subtotal=Decimal("100.00"),
        impuestos=Decimal("15.00"),
        total=Decimal("115.00"),
    )


def test_api_rechaza_emision_sin_usuario_autenticado(monkeypatch):
    contexto = Contexto(empresa_id=7, rol=OPERATIVO, usuario=None)
    app.dependency_overrides[get_contexto] = lambda: contexto

    def servicio_no_debe_ejecutarse(*args, **kwargs):
        raise AssertionError("No debe invocarse FacturaService sin usuario")

    monkeypatch.setattr(facturas_api, "FacturaService", servicio_no_debe_ejecutarse)

    try:
        respuesta = TestClient(app).post(
            "/api/sales/101/invoice",
            headers={"X-Empresa-Id": "7"},
        )
    finally:
        app.dependency_overrides.pop(get_contexto, None)

    assert respuesta.status_code == 403
    assert respuesta.json()["error"]["code"] == "USER_SESSION_REQUIRED"


def test_api_emite_factura_con_usuario_operativo(monkeypatch):
    usuario = SimpleNamespace(id=uuid4())
    contexto = Contexto(empresa_id=7, rol=OPERATIVO, usuario=usuario)
    app.dependency_overrides[get_contexto] = lambda: contexto

    llamadas = []

    class FacturaServiceFalso:
        def __init__(self, db, empresa_id):
            llamadas.append({"empresa_id": empresa_id})

        def emitir(self, id_venta):
            llamadas[-1]["id_venta"] = id_venta
            return _factura_falsa()

    monkeypatch.setattr(facturas_api, "FacturaService", FacturaServiceFalso)

    try:
        respuesta = TestClient(app).post("/api/sales/101/invoice")
    finally:
        app.dependency_overrides.pop(get_contexto, None)

    assert respuesta.status_code == 201
    assert llamadas == [{"empresa_id": 7, "id_venta": 101}]

    datos = respuesta.json()
    assert datos["id"] == 501
    assert datos["saleId"] == 101
    assert datos["invoiceNumber"] == "001-001-000000001"
    assert datos["accessKey"] == "1234567890123456789012345678901234567890123456789"
    assert datos["authorizationStatus"] == "autorizada"
    assert datos["authorizationNumber"] == "1234567890"
    assert datos["subtotal"] == 100.0
    assert datos["taxes"] == 15.0
    assert datos["total"] == 115.0
    assert datos["messages"] == [
        {
            "identifier": "70",
            "message": "Comprobante autorizado",
            "additionalInformation": None,
            "type": "INFORMATIVO",
        }
    ]


def test_api_propaga_conflicto_si_venta_ya_tiene_factura(monkeypatch):
    usuario = SimpleNamespace(id=uuid4())
    contexto = Contexto(empresa_id=7, rol=OPERATIVO, usuario=usuario)
    app.dependency_overrides[get_contexto] = lambda: contexto

    class FacturaServiceFalso:
        def __init__(self, db, empresa_id):
            pass

        def emitir(self, id_venta):
            from app.core.errors import ConflictError

            raise ConflictError("La venta ya tiene una factura.")

    monkeypatch.setattr(facturas_api, "FacturaService", FacturaServiceFalso)

    try:
        respuesta = TestClient(app).post("/api/sales/101/invoice")
    finally:
        app.dependency_overrides.pop(get_contexto, None)

    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "CONFLICT"
    assert respuesta.json()["error"]["message"] == "La venta ya tiene una factura."


def test_api_rechaza_id_de_venta_invalido(monkeypatch):
    usuario = SimpleNamespace(id=uuid4())
    contexto = Contexto(empresa_id=7, rol=OPERATIVO, usuario=usuario)
    app.dependency_overrides[get_contexto] = lambda: contexto

    def servicio_no_debe_ejecutarse(*args, **kwargs):
        raise AssertionError("No debe invocarse el servicio con un ID inválido")

    monkeypatch.setattr(facturas_api, "FacturaService", servicio_no_debe_ejecutarse)

    try:
        respuesta = TestClient(app).post("/api/sales/0/invoice")
    finally:
        app.dependency_overrides.pop(get_contexto, None)

    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "VALIDATION_ERROR"


def test_api_rechaza_descarga_ride_sin_usuario_autenticado(monkeypatch):
    contexto = Contexto(empresa_id=7, rol=OPERATIVO, usuario=None)
    app.dependency_overrides[get_contexto] = lambda: contexto

    def servicio_no_debe_ejecutarse(*args, **kwargs):
        raise AssertionError("No debe invocarse FacturaService sin usuario")

    monkeypatch.setattr(facturas_api, "FacturaService", servicio_no_debe_ejecutarse)

    try:
        respuesta = TestClient(app).get("/api/sales/101/invoice/ride")
    finally:
        app.dependency_overrides.pop(get_contexto, None)

    assert respuesta.status_code == 403
    assert respuesta.json()["error"]["code"] == "USER_SESSION_REQUIRED"


def test_api_descarga_ride_con_usuario_autenticado(monkeypatch):
    usuario = SimpleNamespace(id=uuid4())
    contexto = Contexto(empresa_id=7, rol=OPERATIVO, usuario=usuario)
    app.dependency_overrides[get_contexto] = lambda: contexto

    pdf = b"%PDF-1.4 RIDE de prueba"
    llamadas = []

    class FacturaServiceFalso:
        def __init__(self, db, empresa_id):
            llamadas.append({"empresa_id": empresa_id})

        def obtener_ride(self, id_venta):
            llamadas[-1]["id_venta"] = id_venta
            return pdf

    monkeypatch.setattr(facturas_api, "FacturaService", FacturaServiceFalso)

    try:
        respuesta = TestClient(app).get("/api/sales/101/invoice/ride")
    finally:
        app.dependency_overrides.pop(get_contexto, None)

    assert respuesta.status_code == 200
    assert respuesta.content == pdf
    assert respuesta.headers["content-type"] == "application/pdf"
    assert respuesta.headers["content-disposition"] == ('inline; filename="factura-101-ride.pdf"')
    assert llamadas == [{"empresa_id": 7, "id_venta": 101}]
