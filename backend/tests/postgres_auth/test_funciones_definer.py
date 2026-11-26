"""Funciones SECURITY DEFINER y operaciones del Administrador sobre usuarios y membresías.

1. Reproduce el fallo: con las funciones a nombre de un rol sin BYPASSRLS (iondu_migrator),
   el RLS forzado les oculta las filas y devuelven false; la migración e1f3a5b7c902 lo corrige.
2. iondu_funciones (dueño) solo lee lo necesario; nadie más ejecuta lo que no le corresponde.
3. Regresión de las operaciones del Administrador por la API, con los roles reales.
"""

from datetime import timedelta

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_emisor
from app.core.seguridad import EmisorTokens
from app.db.session import APISession, get_auth_db, get_db
from app.main import app
from tests.postgres_auth.conftest import (
    ANA,
    BETO,
    CONTRASENA,
    CORREOS,
    INACTIVO,
    MULTI,
    OSCAR,
    PREFIJO,
    admin,
    borrar_base,
    como,
    crear_base,
    migrar,
    motor,
    sembrar,
)
from tests.tokens import LLAVE_IONDU

DENEGADO = psycopg.errors.InsufficientPrivilege
ANTES_DE_LA_CORRECCION = "c4e6a8b0d215"
FUNCIONES_APP = ("app_es_admin_de", "app_usuario_en_otras_empresas")


def _contexto(conn, usuario, empresa) -> None:
    conn.execute(
        "SELECT set_config('app.current_user_id', %s, false), "
        "set_config('app.current_empresa_id', %s, false)",
        (str(usuario), str(empresa)),
    )


def _vista_del_admin(base: str, empresa: int) -> dict:
    """Lo que ve la Administradora de A con iondu_app."""
    with como(base, "iondu_app") as conn:
        _contexto(conn, ANA, empresa)
        return {
            "es_admin": conn.execute("SELECT public.app_es_admin_de(%s)", (empresa,)).fetchone()[0],
            "multi_en_otras": conn.execute(
                "SELECT public.app_usuario_en_otras_empresas(%s, %s)", (MULTI, empresa)
            ).fetchone()[0],
            "miembros": conn.execute(
                "SELECT count(*) FROM usuario_empresa WHERE id_empresa = %s", (empresa,)
            ).fetchone()[0],
            "auditoria": conn.execute("SELECT count(*) FROM auditoria").fetchone()[0],
        }


# ---------- 1. El fallo y su corrección ----------
def test_con_un_dueno_sin_bypassrls_las_funciones_fallan_y_la_migracion_lo_corrige(cluster):
    nombre = f"{PREFIJO}funciones"
    crear_base(nombre)
    try:
        migrar(nombre, "upgrade", ANTES_DE_LA_CORRECCION)
        _habilitar_login_app(nombre)
        empresas = sembrar(nombre)
        a = empresas["A"]
        with admin(nombre) as conn:
            conn.execute(
                "INSERT INTO auditoria (id_empresa, id_usuario, modulo, accion, descripcion) "
                "VALUES (%s, %s, 'usuarios', 'Prueba', 'Registro de prueba')",
                (a, ANA),
            )
            # Como en la base del equipo: las funciones a nombre de iondu_migrator.
            conn.execute(
                "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = "
                "'iondu_migrator') THEN CREATE ROLE iondu_migrator NOLOGIN NOSUPERUSER "
                "NOBYPASSRLS; END IF; END $$"
            )
            # Con permisos amplios sobre las tablas (como en esa base) pero sin BYPASSRLS. Sin
            # SELECT, las funciones fallarían con "permission denied" en lugar de dar false.
            conn.execute("GRANT ALL ON ALL TABLES IN SCHEMA public TO iondu_migrator")
            conn.execute("GRANT CREATE ON SCHEMA public TO iondu_migrator")
            for funcion in (
                "app_es_admin_de(integer)",
                "app_usuario_en_otras_empresas(uuid, integer)",
            ):
                conn.execute(f"ALTER FUNCTION public.{funcion} OWNER TO iondu_migrator")
            conn.execute("REVOKE CREATE ON SCHEMA public FROM iondu_migrator")

        assert _vista_del_admin(nombre, a) == {
            "es_admin": False,  # el RLS le oculta todo al dueño
            "multi_en_otras": False,  # ¡diría que no trabaja en otra empresa!
            "miembros": 1,  # solo se ve a sí misma
            "auditoria": 0,
        }

        migrar(nombre, "upgrade", "head")
        assert _vista_del_admin(nombre, a) == {
            "es_admin": True,
            "multi_en_otras": True,
            "miembros": 4,
            "auditoria": 1,
        }
        with admin(nombre) as conn:
            duenos = {
                n: d
                for n, d in conn.execute(
                    "SELECT proname, pg_get_userbyid(proowner) FROM pg_proc "
                    "WHERE proname IN ('app_es_admin_de', 'app_usuario_en_otras_empresas', "
                    "'auth_puede_restablecer')"
                )
            }
        assert duenos == dict.fromkeys(
            (*FUNCIONES_APP, "auth_puede_restablecer"), "iondu_funciones"
        )
    finally:
        borrar_base(nombre)


def _habilitar_login_app(nombre: str) -> None:
    with admin(nombre) as conn:
        conn.execute("ALTER ROLE iondu_app LOGIN PASSWORD 'prueba_app'")


# ---------- 2. Privilegios de iondu_funciones y de las funciones ----------
def test_iondu_funciones_no_inicia_sesion_y_solo_lee_lo_necesario(base):
    with admin(base["nombre"]) as conn:
        atributos = conn.execute(
            "SELECT rolcanlogin, rolsuper, rolbypassrls, rolcreaterole FROM pg_roles "
            "WHERE rolname = 'iondu_funciones'"
        ).fetchone()
        assert atributos == (False, False, False, False)
        privilegios = {
            (t, c, p)
            for t, c, p in conn.execute(
                """
                SELECT c.relname, a.attname, p.privilege_type
                FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid,
                     aclexplode(a.attacl) p
                WHERE p.grantee = 'iondu_funciones'::regrole
                UNION ALL
                SELECT c.relname, NULL, p.privilege_type FROM pg_class c, aclexplode(c.relacl) p
                WHERE p.grantee = 'iondu_funciones'::regrole
                """
            )
        }
        assert privilegios == {
            ("usuario_empresa", "id_usuario", "SELECT"),
            ("usuario_empresa", "id_empresa", "SELECT"),
            ("usuario_empresa", "id_rol", "SELECT"),
            ("usuario_empresa", "estado", "SELECT"),
            ("rol", "id_rol", "SELECT"),
            ("rol", "nombre", "SELECT"),
        }
        assert not conn.execute(
            "SELECT has_schema_privilege('iondu_funciones', 'public', 'CREATE')"
        ).fetchone()[0]


def test_cada_funcion_la_ejecuta_solo_su_rol(base):
    with admin(base["nombre"]) as conn:
        ejecutores = {
            (f, r)
            for f, r in conn.execute(
                """
                SELECT p.proname, CASE WHEN a.grantee = 0 THEN 'PUBLIC'
                                       ELSE pg_get_userbyid(a.grantee) END
                FROM pg_proc p, aclexplode(coalesce(p.proacl, acldefault('f', p.proowner))) a
                WHERE p.proname IN ('app_es_admin_de', 'app_usuario_en_otras_empresas',
                                    'auth_puede_restablecer')
                  AND a.privilege_type = 'EXECUTE' AND a.grantee <> p.proowner
                """
            )
        }
    assert ejecutores == {
        ("app_es_admin_de", "iondu_app"),
        ("app_usuario_en_otras_empresas", "iondu_app"),
        ("auth_puede_restablecer", "iondu_auth"),
    }


def test_iondu_auth_responde_membresias_sin_leer_usuario_empresa(base):
    a = base["empresas"]["A"]
    with como(base["nombre"], "iondu_auth") as conn:
        consulta = "SELECT public.auth_puede_restablecer(%s, %s)"
        assert conn.execute(consulta, (OSCAR, a)).fetchone()[0] == "OK"
        assert conn.execute(consulta, (MULTI, a)).fetchone()[0] == "OTRA_EMPRESA"
        assert conn.execute(consulta, (BETO, a)).fetchone()[0] == "NO_PERTENECE"
        assert conn.execute(consulta, (None, a)).fetchone()[0] == "NO_PERTENECE"
        for sentencia in (
            "SELECT id_usuario FROM usuario_empresa",
            "SELECT count(*) FROM usuario_empresa",
            "SELECT public.app_es_admin_de(1)",
        ):
            with pytest.raises(DENEGADO):
                conn.execute(sentencia)
    with como(base["nombre"], "iondu_app") as conn, pytest.raises(DENEGADO):
        conn.execute("SELECT public.auth_puede_restablecer(%s, %s)", (OSCAR, a))
    with como(base["nombre"], "iondu_worker") as conn:
        for funcion in ("auth_puede_restablecer(NULL, 1)", "app_es_admin_de(1)"):
            with pytest.raises(DENEGADO):
                conn.execute(f"SELECT public.{funcion}")


# ---------- 3. Operaciones del Administrador por la API ----------
@pytest.fixture
def api(base):
    m_app, m_auth = motor(base["nombre"], "iondu_app"), motor(base["nombre"], "iondu_auth")
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
        m_app.dispose()
        m_auth.dispose()
        with admin(base["nombre"]) as conn:
            conn.execute("DELETE FROM sesion_refresh")


def _cabeceras(api, usuario, empresa) -> dict[str, str]:
    respuesta = api.post(
        "/api/auth/login", json={"email": CORREOS[usuario], "password": CONTRASENA}
    )
    assert respuesta.status_code == 200, respuesta.text
    return {
        "Authorization": f"Bearer {respuesta.json()['accessToken']}",
        "X-Empresa-Id": str(empresa),
    }


def test_el_administrador_lista_los_usuarios_de_su_empresa(api, base):
    cabeceras = _cabeceras(api, ANA, base["empresas"]["A"])
    respuesta = api.get("/api/users", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    assert {u["email"] for u in respuesta.json()} == {
        CORREOS[u] for u in (ANA, OSCAR, INACTIVO, MULTI)
    }


def test_el_operativo_no_gestiona_usuarios(api, base):
    cabeceras = _cabeceras(api, OSCAR, base["empresas"]["A"])
    assert api.get("/api/users", headers=cabeceras).status_code == 403


def test_el_administrador_edita_rol_y_estado_de_una_membresia(api, base):
    cabeceras = _cabeceras(api, ANA, base["empresas"]["A"])
    url = f"/api/users/{OSCAR}"
    try:
        respuesta = api.patch(url, json={"role": "admin"}, headers=cabeceras)
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["role"] == "admin"
        respuesta = api.patch(url, json={"role": "operator", "active": False}, headers=cabeceras)
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["active"] is False
    finally:
        api.patch(url, json={"role": "operator", "active": True}, headers=cabeceras)


def test_el_administrador_no_puede_cambiarse_a_si_mismo(api, base):
    cabeceras = _cabeceras(api, ANA, base["empresas"]["A"])
    respuesta = api.patch(f"/api/users/{ANA}", json={"role": "operator"}, headers=cabeceras)
    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "CANNOT_MODIFY_SELF"


def test_no_edita_membresias_de_otra_empresa(api, base):
    cabeceras = _cabeceras(api, ANA, base["empresas"]["A"])
    respuesta = api.patch(f"/api/users/{BETO}", json={"role": "operator"}, headers=cabeceras)
    assert respuesta.status_code == 404


def test_el_administrador_ve_la_auditoria_de_su_empresa(api, base):
    cabeceras = _cabeceras(api, ANA, base["empresas"]["A"])
    api.patch(f"/api/users/{OSCAR}", json={"fullName": "Oscar O."}, headers=cabeceras)
    respuesta = api.get("/api/audit", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["total"] >= 1
    api.patch(f"/api/users/{OSCAR}", json={"fullName": "Oscar"}, headers=cabeceras)
