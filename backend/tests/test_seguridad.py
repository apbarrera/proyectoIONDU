"""Emisión y verificación de los tokens de acceso (sin base de datos ni red).

Los tokens válidos se prueban directamente con el verificador; los inválidos, contra
/api/me, que debe rechazarlos antes de consultar la base.
"""

import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi.testclient import TestClient

from app.api.deps import get_verificador
from app.core.config import get_settings
from app.core.errors import UnauthenticatedError
from app.core.seguridad import EmisorTokens, cargar_llave_privada
from app.main import app
from tests.tokens import EMISOR, LLAVE_ATACANTE, LLAVE_IONDU, crear_token, verificador_de_prueba

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
    publica = LLAVE_IONDU.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    datos = {"sub": str(USUARIO), "aud": "iondu-api", "iss": EMISOR}
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
        {"iss": "https://otro-proyecto.supabase.co/auth/v1"},  # token de otro emisor
        {"aud": "authenticated"},  # token para otra API
        {"sub": "no-es-un-uuid"},
        {"sub": None},
        {"exp": None},
    ],
)
def test_datos_del_token_que_no_corresponden(cambios):
    assert _rechazado(_token(**cambios))


# ---------- Configuración, llave y emisor ----------
def _pem(llave) -> str:
    return llave.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()


def test_sin_llave_configurada_no_se_puede_iniciar_sesion(monkeypatch):
    app.dependency_overrides.clear()
    monkeypatch.setenv("AUTH_JWT_PRIVATE_KEY", "")
    get_settings.cache_clear()
    try:
        response = _me(_token())
    finally:
        get_settings.cache_clear()
    assert response.status_code == 401
    assert "AUTH_JWT_PRIVATE_KEY" in response.json()["error"]["message"]


def test_la_llave_se_acepta_en_una_sola_linea_como_en_env():
    pem = _pem(LLAVE_IONDU).replace("\n", "\\n")
    assert "\n" not in pem
    assert cargar_llave_privada(pem).private_numbers() == LLAVE_IONDU.private_numbers()


@pytest.mark.parametrize(
    "llave",
    [
        ec.generate_private_key(ec.SECP384R1()),  # ES384, no ES256
        rsa.generate_private_key(public_exponent=65537, key_size=2048),
    ],
)
def test_rechaza_llaves_que_no_son_ec_p256(llave):
    with pytest.raises(ValueError, match="P-256"):
        cargar_llave_privada(_pem(llave))


def test_rechaza_texto_que_no_es_una_llave():
    with pytest.raises(ValueError, match="PEM"):
        cargar_llave_privada("no-es-una-llave")


def test_el_emisor_firma_tokens_que_su_verificador_acepta():
    emisor = EmisorTokens(LLAVE_IONDU, duracion=timedelta(minutes=15))
    token = emisor.emitir(USUARIO, "ana@empresa.ec")
    usuario = emisor.verificador().verificar(token)
    assert (usuario.id, usuario.email) == (USUARIO, "ana@empresa.ec")
    assert emisor.duracion_segundos == 900
    assert jwt.get_unverified_header(token)["alg"] == "ES256"


def test_el_token_del_emisor_vence_segun_la_duracion():
    emisor = EmisorTokens(LLAVE_IONDU, duracion=timedelta(minutes=15))
    viejo = emisor.emitir(USUARIO, "ana@empresa.ec", ahora=datetime.now(UTC) - timedelta(hours=1))
    with pytest.raises(UnauthenticatedError) as error:
        emisor.verificador().verificar(viejo)
    assert error.value.code == "TOKEN_EXPIRED"


def test_el_verificador_rechaza_directamente_un_token_falso():
    with pytest.raises(UnauthenticatedError):
        verificador_de_prueba().verificar(_token(llave=LLAVE_ATACANTE))
