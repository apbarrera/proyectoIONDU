"""Formato único de errores y acceso por empresa (no necesitan base de datos)."""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app

client = TestClient(app)


def test_sin_empresa_responde_401_con_formato_estandar():
    response = client.get("/api/products")
    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "UNAUTHENTICATED",
            "message": "Inicia sesión para continuar.",
            "details": [],
        }
    }


def test_en_produccion_el_encabezado_de_empresa_se_ignora(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    try:
        response = client.get("/api/products", headers={"X-Empresa-Id": "1"})
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_ruta_inexistente_responde_404_con_formato_estandar():
    response = client.get("/api/no-existe")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_json_mal_formado_responde_400_en_espanol():
    response = client.post(
        "/api/products",
        content=b"{no es json",
        headers={"X-Empresa-Id": "1", "Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["error"] == {
        "code": "BAD_REQUEST",
        "message": "La petición no tiene un formato válido.",
        "details": [],
    }


def test_base_de_datos_caida_responde_503():
    # Puerto 1 en localhost: nadie escucha. En Windows a veces no se rechaza al instante
    # sino que espera ~2 min; el límite de 1 s mantiene la prueba rápida.
    sin_base = create_engine(
        "postgresql+psycopg://x:y@127.0.0.1:1/x", connect_args={"connect_timeout": 1}
    )
    app.dependency_overrides[get_db] = lambda: Session(sin_base)
    try:
        response = client.get("/api/products", headers={"X-Empresa-Id": "1"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
