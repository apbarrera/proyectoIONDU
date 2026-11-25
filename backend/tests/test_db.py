import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import _session_factory, get_engine
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def limpiar_caches():
    """La configuración y la conexión se crean una vez; cada prueba parte de cero."""
    for cached in (get_settings, get_engine, _session_factory):
        cached.cache_clear()
    yield
    for cached in (get_settings, get_engine, _session_factory):
        cached.cache_clear()


def test_health_sin_database_url_informa_not_configured(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    assert client.get("/api/health").json()["database"] == "not_configured"


def test_health_con_base_inaccesible_informa_error_sin_caerse(monkeypatch):
    # Puerto 1 en localhost: nadie escucha, la conexión se rechaza al instante.
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://x:y@127.0.0.1:1/x")
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["database"] == "error"
