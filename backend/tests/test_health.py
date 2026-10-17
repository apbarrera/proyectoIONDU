from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_responde_ok_con_zona_horaria_de_ecuador():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["timezone"] == "America/Guayaquil"
    assert body["time"].endswith("-05:00")


def test_health_solo_vive_bajo_api():
    assert client.get("/health").status_code == 404
