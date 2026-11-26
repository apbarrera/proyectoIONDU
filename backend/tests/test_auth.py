"""Inicio de sesión propio: login, bloqueo, renovación con rotación y cierre de sesión."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.api.auth import COOKIE_REFRESH
from app.api.deps import get_emisor
from app.core import contrasenas
from app.core.seguridad import EmisorTokens
from app.main import app
from app.models import SesionRefresh, Usuario
from app.services.autenticacion import MAX_INTENTOS, hash_token
from tests.tokens import LLAVE_IONDU

CONTRASENA = "Clave-segura-2026"


@pytest.fixture(autouse=True)
def emisor_de_prueba():
    app.dependency_overrides[get_emisor] = lambda: EmisorTokens(
        LLAVE_IONDU, duracion=timedelta(minutes=15)
    )
    yield
    app.dependency_overrides.pop(get_emisor, None)


@pytest.fixture
def usuario(db, empresas, agregar_pertenencia) -> Usuario:
    """Usuaria con contraseña y pertenencia activa a la empresa A."""
    nuevo = Usuario(
        id=uuid.uuid4(), email="ana@empresa.ec", password_hash=contrasenas.hashear(CONTRASENA)
    )
    db.add(nuevo)
    db.flush()
    agregar_pertenencia(nuevo.id, empresas[0])
    return nuevo


def _login(client, email="ana@empresa.ec", password=CONTRASENA):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _codigo(response) -> str:
    return response.json()["error"]["code"]


def _refrescar(client, token: str | None):
    client.cookies.clear()
    headers = {"Cookie": f"{COOKIE_REFRESH}={token}"} if token else {}
    return client.post("/api/auth/refresh", headers=headers)


# ---------- Login ----------
def test_login_entrega_token_que_abre_la_api_y_cookie_httponly(client, usuario):
    response = _login(client)

    assert response.status_code == 200
    cuerpo = response.json()
    assert cuerpo["tokenType"] == "Bearer"
    assert cuerpo["expiresIn"] == 900
    assert cuerpo["user"]["id"] == str(usuario.id)
    assert cuerpo["user"]["email"] == "ana@empresa.ec"
    assert cuerpo["user"]["createdAt"]
    assert response.headers["cache-control"] == "no-store"

    cookie = response.headers["set-cookie"]
    assert f"{COOKIE_REFRESH}=" in cookie
    assert "HttpOnly" in cookie
    assert "Path=/api/auth" in cookie
    assert "SameSite=strict" in cookie

    me = client.get("/api/me", headers={"Authorization": f"Bearer {cuerpo['accessToken']}"})
    assert me.status_code == 200
    assert me.json()["id"] == str(usuario.id)


def test_login_ignora_mayusculas_y_espacios_del_correo(client, usuario):
    assert _login(client, email="  Ana@Empresa.EC ").status_code == 200


def test_login_guarda_solo_el_hash_del_token_de_renovacion(client, db, usuario):
    response = _login(client)
    token = response.cookies[COOKIE_REFRESH]

    hashes = db.scalars(
        select(SesionRefresh.token_hash).where(SesionRefresh.id_usuario == usuario.id)
    ).all()
    assert hashes == [hash_token(token)]
    assert token not in hashes


@pytest.mark.parametrize(
    ("email", "password"),
    [("ana@empresa.ec", "otra-clave-123"), ("nadie@empresa.ec", CONTRASENA)],
)
def test_credenciales_incorrectas_responden_igual_exista_o_no_el_correo(
    client, usuario, email, password
):
    response = _login(client, email=email, password=password)
    assert (response.status_code, _codigo(response)) == (401, "INVALID_CREDENTIALS")
    assert response.json()["error"]["message"] == "Correo o contraseña incorrectos."


def test_cuenta_sin_contrasena_utilizable_no_entra(client, db, usuario):
    usuario.password_hash = "!"
    db.flush()
    assert _codigo(_login(client, password="!")) == "INVALID_CREDENTIALS"


def test_cuenta_desactivada_no_entra_aunque_la_contrasena_sea_correcta(client, db, usuario):
    usuario.activo = False
    db.flush()
    assert _codigo(_login(client)) == "INVALID_CREDENTIALS"


def test_bloquea_la_cuenta_tras_varios_intentos_fallidos(client, db, usuario):
    for _ in range(MAX_INTENTOS):
        assert _login(client, password="incorrecta-123").status_code == 401

    response = _login(client)  # ni con la contraseña correcta mientras dure el bloqueo
    assert (response.status_code, _codigo(response)) == (429, "TOO_MANY_ATTEMPTS")

    db.expire_all()
    assert usuario.bloqueado_hasta > datetime.now(UTC)


def test_login_correcto_reinicia_los_intentos_fallidos(client, db, usuario):
    _login(client, password="incorrecta-123")
    _login(client)
    db.expire_all()
    assert (usuario.intentos_fallidos, usuario.bloqueado_hasta) == (0, None)


def test_login_rechaza_campos_desconocidos(client, usuario):
    response = client.post(
        "/api/auth/login", json={"email": "ana@empresa.ec", "password": CONTRASENA, "rol": "x"}
    )
    assert response.status_code == 422


# ---------- Renovación ----------
def test_renovar_entrega_token_nuevo_y_rota_la_cookie(client, usuario):
    original = _login(client).cookies[COOKIE_REFRESH]

    response = _refrescar(client, original)

    assert response.status_code == 200
    assert response.json()["accessToken"]
    assert response.cookies[COOKIE_REFRESH] != original


def test_renovar_sin_cookie_o_con_una_falsa_responde_401(client, usuario):
    for token in (None, "inventado"):
        response = _refrescar(client, token)
        assert (response.status_code, _codigo(response)) == (401, "SESSION_INVALID")


def test_reusar_un_token_rotado_cierra_todas_las_sesiones(client, db, usuario):
    original = _login(client).cookies[COOKIE_REFRESH]
    nuevo = _refrescar(client, original).cookies[COOKIE_REFRESH]

    # El token viejo se reutiliza fuera del margen de gracia: alguien lo copió.
    fila = db.scalar(select(SesionRefresh).where(SesionRefresh.token_hash == hash_token(original)))
    fila.rotada_en = datetime.now(UTC) - timedelta(minutes=5)
    db.flush()

    assert _codigo(_refrescar(client, original)) == "SESSION_INVALID"
    assert _codigo(_refrescar(client, nuevo)) == "SESSION_INVALID"


def test_dentro_del_margen_de_gracia_el_token_rotado_aun_renueva(client, usuario):
    original = _login(client).cookies[COOKIE_REFRESH]
    _refrescar(client, original)

    assert _refrescar(client, original).status_code == 200


def test_token_de_renovacion_vencido_no_sirve(client, db, usuario):
    token = _login(client).cookies[COOKIE_REFRESH]
    fila = db.scalar(select(SesionRefresh).where(SesionRefresh.token_hash == hash_token(token)))
    fila.expira_en = datetime.now(UTC) - timedelta(seconds=1)
    db.flush()

    assert _codigo(_refrescar(client, token)) == "SESSION_INVALID"


def test_usuario_desactivado_no_puede_renovar(client, db, usuario):
    token = _login(client).cookies[COOKIE_REFRESH]
    usuario.activo = False
    db.flush()

    assert _codigo(_refrescar(client, token)) == "SESSION_INVALID"


# ---------- Cierre de sesión ----------
def test_logout_revoca_la_sesion_y_borra_la_cookie(client, usuario):
    token = _login(client).cookies[COOKIE_REFRESH]

    client.cookies.clear()
    response = client.post("/api/auth/logout", headers={"Cookie": f"{COOKIE_REFRESH}={token}"})

    assert response.status_code == 204
    assert f'{COOKIE_REFRESH}=""' in response.headers["set-cookie"]
    assert _codigo(_refrescar(client, token)) == "SESSION_INVALID"


def test_logout_sin_cookie_no_falla(client):
    assert client.post("/api/auth/logout").status_code == 204


# ---------- Configuración ----------
def test_sin_llave_configurada_el_login_responde_503(client, usuario):
    app.dependency_overrides[get_emisor] = lambda: None
    response = _login(client)
    assert (response.status_code, _codigo(response)) == (503, "AUTH_NOT_CONFIGURED")
