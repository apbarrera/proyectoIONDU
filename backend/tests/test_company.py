"""Datos de la empresa y configuración de facturación (necesitan TEST_DATABASE_URL)."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.models import Empresa
from app.models.rol import OPERATIVO
from app.schemas.configuracion_facturacion import ConfiguracionFacturacion
from app.services import empresa as empresa_service
from tests.conftest import con_token

CONFIG = {
    "environment": "pruebas",
    "establishment": "001",
    "emissionPoint": "002",
    "requiredToKeepAccounts": False,
    "rimpe": True,
    "specialTaxpayer": None,
}


def _h(empresa_id: int) -> dict[str, str]:
    return {"X-Empresa-Id": str(empresa_id)}  # desarrollo: rol Administrador


def test_consultar_la_empresa_sin_configurar(client, empresas):
    a, _ = empresas
    response = client.get("/api/company", headers=_h(a))
    assert response.status_code == 200
    assert response.json() == {
        "id": a,
        "ruc": "0990000000001",
        "businessName": "Empresa A",
        "tradeName": None,
        "economicActivity": None,
        "address": None,
        "email": "a@test.ec",
        "electronicSignature": {
            "configured": False,
            "expiresAt": None,
            "expiresSoon": False,
            "expired": False,
            "simulated": False,
        },
        "billing": None,
    }


def test_la_firma_indica_el_modo_simulado_solo_en_pruebas(client, empresas, monkeypatch):
    a, _ = empresas
    monkeypatch.setattr(
        empresa_service, "get_settings", lambda: SimpleNamespace(sri_simulado_empresas={a})
    )
    client.put("/api/company/billing-settings", json=CONFIG, headers=_h(a))
    firma = client.get("/api/company", headers=_h(a)).json()["electronicSignature"]
    assert firma["simulated"] is True

    client.put(
        "/api/company/billing-settings",
        json={**CONFIG, "environment": "produccion"},
        headers=_h(a),
    )
    firma = client.get("/api/company", headers=_h(a)).json()["electronicSignature"]
    assert firma["simulated"] is False  # en producción nunca se simula


def test_editar_solo_cambia_lo_enviado_y_no_acepta_ruc(client, empresas):
    a, _ = empresas
    response = client.put(
        "/api/company",
        json={"tradeName": "Café Demo", "address": "Av. Amazonas N12-34, Quito"},
        headers=_h(a),
    )
    assert response.status_code == 200
    empresa = response.json()
    assert (empresa["tradeName"], empresa["address"]) == ("Café Demo", "Av. Amazonas N12-34, Quito")
    assert empresa["businessName"] == "Empresa A"
    assert (
        client.put("/api/company", json={"ruc": "1790010937001"}, headers=_h(a)).status_code == 422
    )
    vacio = client.put("/api/company", json={"businessName": None}, headers=_h(a))
    assert vacio.status_code == 422


def test_configurar_la_facturacion_en_el_formato_que_lee_la_emision(client, db, empresas):
    a, _ = empresas
    response = client.put("/api/company/billing-settings", json=CONFIG, headers=_h(a))
    assert response.status_code == 200
    assert response.json()["billing"] == CONFIG

    db.expire_all()
    guardado = db.get(Empresa, a).datos_facturacion_electronica
    # Es exactamente lo que valida la facturación al emitir.
    config = ConfiguracionFacturacion.model_validate(guardado)
    assert (config.ambiente, config.establecimiento, config.punto_emision) == ("1", "001", "002")
    assert config.contribuyente_rimpe is True


def test_configuracion_invalida(client, empresas):
    a, _ = empresas
    for cambio in (
        {"establishment": "1"},
        {"emissionPoint": "abc"},
        {"environment": "staging"},
        {"specialTaxpayer": "ABC"},
    ):
        response = client.put("/api/company/billing-settings", json=CONFIG | cambio, headers=_h(a))
        assert response.status_code == 422, cambio


def test_estado_de_la_firma_por_vencer_y_vencida(client, db, empresas):
    a, _ = empresas
    hoy = datetime.now(ZoneInfo("America/Guayaquil")).date()
    empresa = db.get(Empresa, a)
    empresa.certificado_p12_cifrado = "cifrado"
    empresa.certificado_password_cifrada = "cifrada"

    empresa.certificado_fecha_vencimiento = hoy + timedelta(days=20)
    db.flush()
    firma = client.get("/api/company", headers=_h(a)).json()["electronicSignature"]
    assert (firma["configured"], firma["expiresSoon"], firma["expired"]) == (True, True, False)

    empresa.certificado_fecha_vencimiento = hoy - timedelta(days=1)
    db.flush()
    firma = client.get("/api/company", headers=_h(a)).json()["electronicSignature"]
    assert (firma["expiresSoon"], firma["expired"]) == (False, True)


def test_solo_el_administrador_modifica(client, empresas, supabase_falso, nuevo_usuario):
    a, _ = empresas
    operador = nuevo_usuario(a, rol=OPERATIVO)
    assert client.get("/api/company", headers=con_token(operador)).status_code == 200
    for ruta, cuerpo in (
        ("/api/company", {"tradeName": "X"}),
        ("/api/company/billing-settings", CONFIG),
    ):
        response = client.put(ruta, json=cuerpo, headers=con_token(operador))
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "FORBIDDEN"


def test_cada_empresa_ve_y_cambia_solo_la_suya(client, empresas):
    a, b = empresas
    client.put("/api/company", json={"tradeName": "Solo A"}, headers=_h(a))
    assert client.get("/api/company", headers=_h(b)).json()["tradeName"] is None
