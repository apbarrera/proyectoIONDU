"""Autenticación de punta a punta con los roles reales: la API usa iondu_app para el negocio
e iondu_auth para usuario y sesion_refresh. El login y la renovación funcionan sin contexto
de empresa."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.auth import COOKIE_REFRESH
from app.api.deps import get_emisor
from app.core.seguridad import EmisorTokens
from app.db.session import APISession, get_auth_db, get_db
from app.main import app
from app.services.autenticacion import MAX_INTENTOS
from tests.postgres_auth.conftest import (
    ANA,
    BETO,
    CONTRASENA,
    CORREOS,
    INACTIVO,
    MULTI,
    OSCAR,
    admin,
    motor,
)
from tests.tokens import LLAVE_IONDU


@pytest.fixture(scope="module")
def motores(base):
    m_app, m_auth = motor(base["nombre"], "iondu_app"), motor(base["nombre"], "iondu_auth")
    yield m_app, m_auth
    m_app.dispose()
    m_auth.dispose()


@pytest.fixture
def api(motores):
    m_app, m_auth = motores
    negocio = sessionmaker(bind=m_app, class_=APISession, autoflush=False, expire_on_commit=False)
    autenticacion = sessionmaker(bind=m_auth, class_=Session, expire_on_commit=False)

    def sesion_negocio():
        with negocio() as s:
            yield s

    def sesion_auth():
        with autenticacion() as s:
            yield s

    app.dependency_overrides[get_db] = sesion_negocio
    app.dependency_overrides[get_auth_db] = sesion_auth
    app.dependency_overrides[get_emisor] = lambda: EmisorTokens(
        LLAVE_IONDU, duracion=timedelta(minutes=15)
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def restablecer(base):
    """Deja las cuentas sembradas como al principio (contraseña, contadores, sesiones)."""
    yield
    from app.core import contrasenas

    with admin(base["nombre"]) as conn:
        conn.execute(
            "UPDATE usuario SET password_hash = %s, intentos_fallidos = 0, bloqueado_hasta = NULL",
            (contrasenas.hashear(CONTRASENA),),
        )
        conn.execute("DELETE FROM sesion_refresh")


def _login(api, usuario, contrasena=CONTRASENA):
    return api.post("/api/auth/login", json={"email": CORREOS[usuario], "password": contrasena})


def _bearer(respuesta) -> dict[str, str]:
    return {"Authorization": f"Bearer {respuesta.json()['accessToken']}"}


def _sesiones(base, usuario) -> list[tuple]:
    with admin(base["nombre"]) as conn:
        return conn.execute(
            "SELECT token_hash, rotada_en, revocada_en FROM sesion_refresh WHERE id_usuario = %s",
            (usuario,),
        ).fetchall()


# ---------- Login ----------
def test_login_correcto_sin_contexto_de_empresa_y_luego_sus_empresas(api, restablecer):
    respuesta = _login(api, ANA)
    assert respuesta.status_code == 200, respuesta.text
    assert COOKIE_REFRESH in respuesta.cookies
    empresas = api.get("/api/me/companies", headers=_bearer(respuesta))
    assert empresas.status_code == 200, empresas.text
    assert [e["name"] for e in empresas.json()] == ["Empresa A"]


def test_login_incorrecto(api, restablecer):
    respuesta = _login(api, ANA, "otra-clave-equivocada")
    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["code"] == "INVALID_CREDENTIALS"
    respuesta = api.post("/api/auth/login", json={"email": "nadie@x.ec", "password": "x"})
    assert respuesta.status_code == 401


def test_bloqueo_por_intentos_fallidos(api, base, restablecer):
    for _ in range(MAX_INTENTOS):
        assert _login(api, OSCAR, "equivocada").status_code == 401
    # Con la contraseña correcta sigue bloqueado.
    assert _login(api, OSCAR).status_code == 429
    with admin(base["nombre"]) as conn:
        bloqueado = conn.execute(
            "SELECT bloqueado_hasta IS NOT NULL FROM usuario WHERE id = %s", (OSCAR,)
        ).fetchone()[0]
    assert bloqueado


def test_usuario_inactivo_no_inicia_sesion(api, restablecer):
    respuesta = _login(api, INACTIVO)
    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["code"] == "INVALID_CREDENTIALS"


# ---------- Renovación, reutilización y cierre ----------
def test_renovacion_correcta_rota_el_token(api, base, restablecer):
    _login(api, ANA)
    anterior = api.cookies.get(COOKIE_REFRESH)
    respuesta = api.post("/api/auth/refresh")
    assert respuesta.status_code == 200, respuesta.text
    assert api.cookies.get(COOKIE_REFRESH) != anterior
    assert sum(1 for _h, rotada, _r in _sesiones(base, ANA) if rotada is not None) == 1


def test_reutilizar_un_token_rotado_cierra_todas_las_sesiones(api, base, restablecer):
    _login(api, ANA)
    robado = api.cookies.get(COOKIE_REFRESH)
    assert api.post("/api/auth/refresh").status_code == 200
    vigente = api.cookies.get(COOKIE_REFRESH)
    # Pasa el margen de gracia de 30 s (se simula moviendo la marca de rotación).
    with admin(base["nombre"]) as conn:
        conn.execute(
            "UPDATE sesion_refresh SET rotada_en = rotada_en - interval '1 minute' "
            "WHERE rotada_en IS NOT NULL"
        )
    api.cookies.set(COOKIE_REFRESH, robado, path="/api/auth")
    assert api.post("/api/auth/refresh").status_code == 401
    assert all(revocada is not None for _h, _r, revocada in _sesiones(base, ANA))
    api.cookies.set(COOKIE_REFRESH, vigente, path="/api/auth")
    assert api.post("/api/auth/refresh").status_code == 401


def test_logout_revoca_la_sesion(api, base, restablecer):
    _login(api, ANA)
    token = api.cookies.get(COOKIE_REFRESH)
    assert api.post("/api/auth/logout").status_code == 204
    api.cookies.set(COOKIE_REFRESH, token, path="/api/auth")
    assert api.post("/api/auth/refresh").status_code == 401
    assert all(revocada is not None for _h, _r, revocada in _sesiones(base, ANA))


# ---------- Cambio y restablecimiento de contraseña ----------
def test_cambio_de_contrasena_revoca_las_sesiones_anteriores(api, base, restablecer):
    primera = _login(api, OSCAR)
    otra_cookie = api.cookies.get(COOKIE_REFRESH)
    nueva = "Otra-clave-segura-2026"
    respuesta = api.post(
        "/api/me/password",
        json={"currentPassword": CONTRASENA, "newPassword": nueva},
        headers=_bearer(primera),
    )
    assert respuesta.status_code == 200, respuesta.text
    assert _login(api, OSCAR).status_code == 401
    assert _login(api, OSCAR, nueva).status_code == 200
    api.cookies.set(COOKIE_REFRESH, otra_cookie, path="/api/auth")
    assert api.post("/api/auth/refresh").status_code == 401


def test_restablecer_revoca_todas_las_sesiones_del_usuario(api, base, restablecer):
    _login(api, OSCAR)
    cookie_oscar = api.cookies.get(COOKIE_REFRESH)
    sesion_ana = _login(api, ANA)
    empresa_a = base["empresas"]["A"]
    respuesta = api.post(
        f"/api/users/{OSCAR}/reset-password",
        headers=_bearer(sesion_ana) | {"X-Empresa-Id": str(empresa_a)},
    )
    assert respuesta.status_code == 200, respuesta.text
    temporal = respuesta.json()["temporaryPassword"]
    assert all(revocada is not None for _h, _r, revocada in _sesiones(base, OSCAR))
    api.cookies.set(COOKIE_REFRESH, cookie_oscar, path="/api/auth")
    assert api.post("/api/auth/refresh").status_code == 401
    assert _login(api, OSCAR, temporal).status_code == 200


def test_no_se_restablece_la_contrasena_de_quien_trabaja_en_otra_empresa(api, base, restablecer):
    sesion_ana = _login(api, ANA)
    respuesta = api.post(
        f"/api/users/{MULTI}/reset-password",
        headers=_bearer(sesion_ana) | {"X-Empresa-Id": str(base["empresas"]["A"])},
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "USER_IN_OTHER_COMPANY"
    assert _login(api, MULTI).status_code == 200


def test_no_se_restablece_la_contrasena_de_otra_empresa(api, base, restablecer):
    sesion_ana = _login(api, ANA)
    respuesta = api.post(
        f"/api/users/{BETO}/reset-password",
        headers=_bearer(sesion_ana) | {"X-Empresa-Id": str(base["empresas"]["A"])},
    )
    assert respuesta.status_code == 404
    assert _login(api, BETO).status_code == 200


# ---------- Creación de usuarios y membresías ----------
def test_crear_usuario_nuevo_y_agregar_uno_existente(api, base, restablecer):
    sesion_beto = _login(api, BETO)
    cabeceras = _bearer(sesion_beto) | {"X-Empresa-Id": str(base["empresas"]["B"])}
    nuevo = api.post(
        "/api/users",
        json={"email": "Nueva@B.ec", "fullName": "Nueva", "role": "operator"},
        headers=cabeceras,
    )
    assert nuevo.status_code == 201, nuevo.text
    temporal = nuevo.json()["temporaryPassword"]
    assert (
        api.post("/api/auth/login", json={"email": "nueva@b.ec", "password": temporal}).status_code
        == 200
    )

    # Oscar ya existe (trabaja en A): solo se le agrega la membresía, sin tocar su contraseña.
    existente = api.post(
        "/api/users",
        json={"email": CORREOS[OSCAR], "fullName": "Oscar en B", "role": "operator"},
        headers=cabeceras,
    )
    assert existente.status_code == 201, existente.text
    assert existente.json()["temporaryPassword"] is None
    assert _login(api, OSCAR).status_code == 200
    listado = api.get("/api/users", headers=cabeceras)
    assert {u["email"] for u in listado.json()} == {
        CORREOS[BETO],
        CORREOS[MULTI],
        CORREOS[OSCAR],
        "nueva@b.ec",
    }
    with admin(base["nombre"]) as conn:
        conn.execute(
            "DELETE FROM usuario_empresa WHERE id_empresa = %s AND id_usuario IN "
            "(SELECT id FROM usuario WHERE email IN ('nueva@b.ec', %s))",
            (base["empresas"]["B"], CORREOS[OSCAR]),
        )
        conn.execute("DELETE FROM usuario WHERE email = 'nueva@b.ec'")
