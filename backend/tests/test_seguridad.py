"""Verificación de tokens de Supabase (sin base de datos ni red).

Los tokens válidos se prueban directamente con el verificador; los inválidos, contra
/api/me, que debe rechazarlos antes de consultar la base.
"""

import base64
import hashlib
import hmac
import json
import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient

from app.api.deps import get_verificador
from app.core.config import get_settings
from app.core.errors import UnauthenticatedError
from app.core.seguridad import VerificadorTokens
from app.main import app
from tests.tokens import EMISOR, LLAVE_ATACANTE, LLAVE_SUPABASE, crear_token, verificador_de_prueba

USUARIO = uuid.uuid4()
client = TestClient(app)


def _token(**cambios) -> str:
    return crear_token(USUARIO, **cambios)


@pytest.fixture(autouse=True)
def supabase_falso():
    app.dependency_overrides[get_verificador] = verificador_de_prueba
    yield
    app.dependency_overrides.clear()


def _me(token: str | None = None, esquema: str = "Bearer"):
    headers = {"Authorization": f"{esquema} {token}"} if token else {}
    return client.get("/api/me", headers=headers)


def _codigo(response) -> str:
    return response.json()["error"]["code"]


# ---------- Tokens válidos ----------
def test_token_valido_identifica_al_usuario():
    usuario = verificador_de_prueba().verificar(_token())
    assert (usuario.id, usuario.email) == (USUARIO, "ana@empresa.ec")


def test_acepta_hasta_30_segundos_de_diferencia_de_reloj():
    usuario = verificador_de_prueba().verificar(_token(exp=int(time.time()) - 20))
    assert usuario.id == USUARIO


# ---------- Sin sesión o sesión vencida ----------
@pytest.mark.parametrize(("token", "esquema"), [(None, "Bearer"), ("abc", "Basic"), ("", "Bearer")])
def test_sin_token_bearer_responde_401(token, esquema):
    response = _me(token, esquema)
    assert (response.status_code, _codigo(response)) == (401, "UNAUTHENTICATED")


def test_token_vencido_responde_401_con_codigo_propio():
    response = _me(_token(exp=int(time.time()) - 120))
    assert (response.status_code, _codigo(response)) == (401, "TOKEN_EXPIRED")
    assert response.json()["error"]["message"] == "Tu sesión expiró. Inicia sesión de nuevo."


# ---------- Tokens falsos o de otro lugar ----------
def _rechazado(token: str) -> bool:
    response = _me(token)
    return response.status_code == 401 and _codigo(response) == "UNAUTHENTICATED"


def test_firmado_con_otra_llave():
    assert _rechazado(_token(llave=LLAVE_ATACANTE))


def test_token_alterado():
    encabezado, _, firma = _token().split(".")
    otro = _token(sub=str(uuid.uuid4())).split(".")[1]  # datos de otro usuario, firma original
    assert _rechazado(f"{encabezado}.{otro}.{firma}")


def test_ataque_alg_none_token_sin_firma():
    assert _rechazado(_token(llave=None, algoritmo="none"))


def test_ataque_confusion_de_algoritmo_hs256_con_la_llave_publica():
    # El atacante conoce la llave pública (es pública) y la usa como "secreto" de HS256.
    publica = LLAVE_SUPABASE.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    datos = {"sub": str(USUARIO), "aud": "authenticated", "iss": EMISOR}
    datos["exp"] = int(time.time()) + 3600

    def b64(contenido: bytes) -> str:
        return base64.urlsafe_b64encode(contenido).rstrip(b"=").decode()

    # Armado a mano, como lo haría un atacante (PyJWT ni siquiera permite crearlo).
    firmado = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()) + "."
    firmado += b64(json.dumps(datos).encode())
    firma = hmac.new(publica, firmado.encode(), hashlib.sha256).digest()
    assert _rechazado(f"{firmado}.{b64(firma)}")


@pytest.mark.parametrize(
    "cambios",
    [
        {"iss": "https://otro-proyecto.supabase.co/auth/v1"},  # token de otro Supabase
        {"aud": "anon"},  # llave pública anónima, no un usuario
        {"sub": "no-es-un-uuid"},
        {"sub": None},
        {"exp": None},
    ],
)
def test_datos_del_token_que_no_corresponden(cambios):
    assert _rechazado(_token(**cambios))


# ---------- Configuración y servicio ----------
def test_si_supabase_no_responde_al_pedir_las_llaves_es_503():
    def caido(_token):
        raise jwt.PyJWKClientConnectionError("sin conexión")

    app.dependency_overrides[get_verificador] = lambda: VerificadorTokens(EMISOR, caido)
    response = _me(_token())
    assert (response.status_code, _codigo(response)) == (503, "AUTH_UNAVAILABLE")


def test_sin_supabase_configurado_no_se_puede_iniciar_sesion(monkeypatch):
    app.dependency_overrides.clear()
    monkeypatch.setenv("SUPABASE_URL", "")
    get_settings.cache_clear()
    try:
        response = _me(_token())
    finally:
        get_settings.cache_clear()
    assert response.status_code == 401
    assert "SUPABASE_URL" in response.json()["error"]["message"]


def test_para_supabase_usa_las_direcciones_del_proyecto():
    verificador = VerificadorTokens.para_supabase("https://abc123.supabase.co/")
    assert verificador._emisor == "https://abc123.supabase.co/auth/v1"


def test_el_verificador_rechaza_directamente_un_token_falso():
    with pytest.raises(UnauthenticatedError):
        verificador_de_prueba().verificar(_token(llave=LLAVE_ATACANTE))
