"""Las migraciones e1f3a5b7c902 y d6a8c0e2f417 validan iondu_funciones e iondu_auth antes de
cambiar dueÃƒÂ±os, conceder permisos o crear polÃƒÂ­ticas.

- Rol inexistente: se crea NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB NOINHERIT.
- iondu_funciones preexistente: debe cumplir todo eso, NOLOGIN incluido.
- iondu_auth preexistente: puede tener LOGIN o NOLOGIN (la API se conecta con ÃƒÂ©l), pero no
  SUPERUSER, BYPASSRLS, CREATEROLE, CREATEDB ni INHERIT.
- Si un atributo obligatorio no se cumple, la migraciÃƒÂ³n se detiene con un error claro, sin
  cambiar los atributos del rol ni dejar nada aplicado (una sola transacciÃƒÂ³n).
"""

import os
import subprocess
import sys

import psycopg
import pytest

from tests.postgres_auth.conftest import (
    BACKEND,
    CLAVES,
    PREFIJO,
    admin,
    borrar_base,
    crear_base,
    migrar,
    psycopg_url,
    url_de,
)

ANTES = "c4e6a8b0d215"
HEAD = "fd09a182da8d"
ROLES = ("iondu_funciones", "iondu_auth")
ATRIBUTOS = {  # nombre en ALTER ROLE -> columna de pg_roles
    "LOGIN": "rolcanlogin",
    "SUPERUSER": "rolsuper",
    "BYPASSRLS": "rolbypassrls",
    "CREATEROLE": "rolcreaterole",
    "CREATEDB": "rolcreatedb",
    "INHERIT": "rolinherit",
}
COLUMNAS = ", ".join(ATRIBUTOS.values())
SEGURO = dict.fromkeys(ATRIBUTOS, False)

# Combinaciones que deben detener la migraciÃƒÂ³n: todo atributo en iondu_funciones; todos salvo
# LOGIN en iondu_auth.
RECHAZOS = [("iondu_funciones", a) for a in ATRIBUTOS] + [
    ("iondu_auth", a) for a in ATRIBUTOS if a != "LOGIN"
]


def _atributos(conn, rol: str) -> dict[str, bool] | None:
    fila = conn.execute(f"SELECT {COLUMNAS} FROM pg_roles WHERE rolname = %s", (rol,)).fetchone()
    return dict(zip(ATRIBUTOS, fila, strict=True)) if fila else None


def _fijar(conn, rol: str, valores: dict[str, bool]) -> None:
    conn.execute(
        f"ALTER ROLE {rol} " + " ".join(("" if v else "NO") + a for a, v in valores.items())
    )


def _alembic(base: str, *argumentos: str) -> subprocess.CompletedProcess:
    """Alembic tal cual, devolviendo el resultado (tambiÃƒÂ©n cuando falla)."""
    return subprocess.run(
        [sys.executable, "-m", "alembic", *argumentos],
        cwd=BACKEND,
        env={**os.environ, "MIGRATION_DATABASE_URL": url_de(base)},
        capture_output=True,
        text=True,
    )


def _version(base: str) -> str:
    with admin(base) as conn:
        return conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]


# ---------- Rol inexistente ----------
def test_si_los_roles_no_existen_se_crean_con_los_atributos_exigidos(cluster):
    """Los roles son globales: los existentes se apartan con otro nombre durante la prueba."""
    nombre = f"{PREFIJO}roles_nuevos"
    apartados = []
    with admin("postgres") as conn:
        for rol in ROLES:
            if _atributos(conn, rol) is not None:
                conn.execute(f"ALTER ROLE {rol} RENAME TO {rol}_apartado")
                apartados.append(rol)
    try:
        crear_base(nombre)
        migrar(nombre, "upgrade", "head")
        with admin(nombre) as conn:
            for rol in ROLES:
                assert _atributos(conn, rol) == SEGURO, rol
    finally:
        borrar_base(nombre)
        with admin("postgres") as conn:
            for rol in ROLES:
                conn.execute(f"DROP ROLE IF EXISTS {rol}")
            for rol in apartados:
                conn.execute(f"ALTER ROLE {rol}_apartado RENAME TO {rol}")


# ---------- Roles preexistentes ----------
@pytest.fixture(scope="module")
def base_previa(cluster):
    """Base en la migraciÃƒÂ³n anterior a e1f3a5b7c902, con los roles ya creados."""
    nombre = f"{PREFIJO}roles_previa"
    crear_base(nombre)
    with admin(nombre) as conn:
        for rol in ROLES:
            if _atributos(conn, rol) is None:
                conn.execute(f"CREATE ROLE {rol} " + " ".join("NO" + a for a in ATRIBUTOS))
    migrar(nombre, "upgrade", ANTES)
    yield nombre
    borrar_base(nombre)


@pytest.fixture
def roles_restaurados(base_previa):
    """Guarda los atributos de ambos roles y los restaura al terminar (son globales)."""
    with admin(base_previa) as conn:
        originales = {rol: _atributos(conn, rol) for rol in ROLES}
    yield
    with admin(base_previa) as conn:
        for rol, valores in originales.items():
            _fijar(conn, rol, valores)
    resultado = _alembic(base_previa, "downgrade", ANTES)
    assert resultado.returncode == 0, resultado.stderr[-2000:]


def _estado(base: str) -> tuple:
    with admin(base) as conn:
        return (
            conn.execute("SELECT version_num FROM alembic_version").fetchone()[0],
            conn.execute(
                "SELECT proname, pg_get_userbyid(proowner) FROM pg_proc "
                "WHERE pronamespace = 'public'::regnamespace ORDER BY 1"
            ).fetchall(),
            conn.execute("SELECT count(*) FROM pg_policies").fetchone()[0],
            conn.execute(
                "SELECT relrowsecurity FROM pg_class WHERE relname = 'usuario'"
            ).fetchone()[0],
        )


@pytest.mark.parametrize("login", (True, False), ids=("LOGIN", "NOLOGIN"))
def test_iondu_auth_con_login_o_sin_login_pasa_la_validacion(base_previa, roles_restaurados, login):
    with admin(base_previa) as conn:
        _fijar(conn, "iondu_funciones", SEGURO)
        _fijar(conn, "iondu_auth", SEGURO | {"LOGIN": login})
    resultado = _alembic(base_previa, "upgrade", "head")
    assert resultado.returncode == 0, resultado.stderr[-2000:]
    assert _version(base_previa) == HEAD
    with admin(base_previa) as conn:
        # La migraciÃƒÂ³n no tocÃƒÂ³ los atributos.
        assert _atributos(conn, "iondu_auth") == SEGURO | {"LOGIN": login}


@pytest.mark.parametrize(("rol", "atributo"), RECHAZOS)
def test_un_atributo_obligatorio_incumplido_detiene_la_migracion(
    base_previa, roles_restaurados, rol, atributo
):
    with admin(base_previa) as conn:
        _fijar(conn, "iondu_funciones", SEGURO)
        # iondu_auth con LOGIN (permitido) para comprobar que solo falla por el atributo.
        _fijar(conn, "iondu_auth", SEGURO | {"LOGIN": True})
        _fijar(conn, rol, _atributos(conn, rol) | {atributo: True})
    antes = _estado(base_previa)

    resultado = _alembic(base_previa, "upgrade", "head")

    assert resultado.returncode != 0
    assert f"El rol {rol} ya existe con atributos no permitidos: {atributo}" in resultado.stderr
    assert "no cambia atributos" in resultado.stderr
    # Nada quedÃƒÂ³ aplicado y el rol conserva el atributo (no se corrigiÃƒÂ³ en silencio).
    assert _estado(base_previa) == antes
    with admin(base_previa) as conn:
        assert _atributos(conn, rol)[atributo] is True


# ---------- Bajar y volver a subir con iondu_auth en uso ----------
def test_bajar_y_volver_a_subir_sin_quitar_login_a_iondu_auth(cluster):
    nombre = f"{PREFIJO}roles_ciclo"
    crear_base(nombre)
    try:
        migrar(nombre, "upgrade", "head")
        with admin(nombre) as conn:
            original = _atributos(conn, "iondu_auth")
            conn.execute(f"ALTER ROLE iondu_auth LOGIN PASSWORD '{CLAVES['iondu_auth']}'")
        try:
            for argumentos in (("downgrade", ANTES), ("upgrade", "head")):
                resultado = _alembic(nombre, *argumentos)
                assert resultado.returncode == 0, resultado.stderr[-2000:]
            assert _version(nombre) == HEAD
            # El rol sigue con LOGIN y su contraseÃƒÂ±a sigue sirviendo.
            with psycopg.connect(psycopg_url(url_de(nombre, "iondu_auth"))) as conn:
                assert conn.execute("SELECT current_user").fetchone()[0] == "iondu_auth"
        finally:
            with admin(nombre) as conn:
                _fijar(conn, "iondu_auth", original)
    finally:
        borrar_base(nombre)
