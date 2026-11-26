"""AutenticaciÃ³n, aislamiento y privilegios contra un PostgreSQL REAL con las migraciones.

El resto de la suite crea las tablas con `create_all` (sin RLS ni permisos). AquÃ­ la base
se crea con `alembic upgrade head` y la API se conecta como iondu_app (negocio) e
iondu_auth (autenticaciÃ³n), como en producciÃ³n. Las pruebas directas de SQL inician sesiÃ³n
con esos roles y con iondu_worker.

Los roles de PostgreSQL son globales y estas pruebas les asignan contraseÃ±as: necesitan un
clÃºster DESECHABLE y se niegan a correr si encuentran otra base (por ejemplo, iondu).

    docker run -d --rm --name iondu-pg-auth -p 127.0.0.1:26432:5432 \\
        -e POSTGRES_USER=iondu -e POSTGRES_PASSWORD=pruebas -e POSTGRES_DB=postgres \\
        postgres:17-alpine
    TEST_ADMIN_DATABASE_URL=postgresql+psycopg://iondu:pruebas@127.0.0.1:26432/postgres
    pytest tests/postgres_auth

Sin TEST_ADMIN_DATABASE_URL se omiten; con IONDU_REQUIRE_DB=1 (CI) fallan en su lugar.
"""

import os
import subprocess
import sys
import uuid
from pathlib import Path

import psycopg
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from app.core import contrasenas
from app.core.config import TIMEZONE

ADMIN_URL = os.environ.get("TEST_ADMIN_DATABASE_URL")
BACKEND = Path(__file__).resolve().parents[2]
HOSTS_LOCALES = {"127.0.0.1", "localhost", "db", "postgres"}
BASES_PERMITIDAS = {"postgres", "template0", "template1", "iondu_test", "iondu_migraciones"}
PREFIJO = "iondu_pgauth_"
HEAD = "fd09a182da8d"
PREVIA = "c4e6a8b0d215"

CLAVES = {"iondu_app": "prueba_app", "iondu_auth": "prueba_auth", "iondu_worker": "prueba_worker"}
CONTRASENA = "Clave-segura-2026"

ANA = uuid.UUID("a0000000-0000-4000-8000-000000000001")  # Administradora de A
OSCAR = uuid.UUID("a0000000-0000-4000-8000-000000000002")  # Operativo de A
INACTIVO = uuid.UUID("a0000000-0000-4000-8000-000000000003")  # cuenta desactivada, en A
MULTI = uuid.UUID("a0000000-0000-4000-8000-000000000004")  # Operativo de A y de B
BETO = uuid.UUID("b0000000-0000-4000-8000-000000000001")  # Administrador de B
CORREOS = {
    ANA: "ana@a.ec",
    OSCAR: "oscar@a.ec",
    INACTIVO: "ines@a.ec",
    MULTI: "multi@ab.ec",
    BETO: "beto@b.ec",
}


def psycopg_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def url_de(base: str, rol: str | None = None) -> str:
    url = make_url(ADMIN_URL).set(database=base)
    if rol:
        url = url.set(username=rol, password=CLAVES[rol])
    return url.render_as_string(hide_password=False)


def admin(base: str) -> psycopg.Connection:
    return psycopg.connect(psycopg_url(url_de(base)), autocommit=True)


def como(base: str, rol: str) -> psycopg.Connection:
    return psycopg.connect(psycopg_url(url_de(base, rol)), autocommit=True)


def motor(base: str, rol: str):
    return create_engine(url_de(base, rol), connect_args={"options": f"-c timezone={TIMEZONE}"})


def alembic(base: str, *argumentos: str) -> None:
    """Ejecuta el comando real de Alembic, como en el CI y en el despliegue."""
    entorno = {**os.environ, "MIGRATION_DATABASE_URL": url_de(base)}
    resultado = subprocess.run(
        [sys.executable, "-m", "alembic", *argumentos],
        cwd=BACKEND,
        env=entorno,
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stderr[-3000:]


def migrar(base: str, *argumentos: str) -> None:
    """Alembic tal cual, sin preparar los roles: iondu_auth puede tener LOGIN (se lo dan las
    pruebas de API) y las migraciones deben poder subir y bajar igual."""
    alembic(base, *argumentos)


def crear_base(nombre: str) -> None:
    assert nombre.startswith(PREFIJO)
    with psycopg.connect(psycopg_url(ADMIN_URL), autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{nombre}" WITH (FORCE)')
        conn.execute(f'CREATE DATABASE "{nombre}"')


def borrar_base(nombre: str) -> None:
    with psycopg.connect(psycopg_url(ADMIN_URL), autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{nombre}" WITH (FORCE)')


@pytest.fixture(scope="session")
def cluster():
    if not ADMIN_URL:
        if os.environ.get("IONDU_REQUIRE_DB") == "1":
            pytest.fail("IONDU_REQUIRE_DB=1 pero falta TEST_ADMIN_DATABASE_URL")
        pytest.skip("Define TEST_ADMIN_DATABASE_URL para las pruebas con PostgreSQL real")
    if make_url(ADMIN_URL).host not in HOSTS_LOCALES:
        pytest.fail("TEST_ADMIN_DATABASE_URL debe apuntar a un PostgreSQL local")
    with psycopg.connect(psycopg_url(ADMIN_URL), autocommit=True) as conn:
        if int(conn.execute("SHOW server_version_num").fetchone()[0]) < 170000:
            pytest.fail("Se requiere PostgreSQL 17")
        if not conn.execute(
            "SELECT rolsuper FROM pg_roles WHERE rolname = current_user"
        ).fetchone()[0]:
            pytest.fail("TEST_ADMIN_DATABASE_URL debe ser superusuario del clÃºster desechable")
        ajenas = sorted(
            b
            for (b,) in conn.execute("SELECT datname FROM pg_database")
            if b not in BASES_PERMITIDAS and not b.startswith(PREFIJO)
        )
        if ajenas:
            pytest.fail(
                "El clÃºster no es desechable: contiene " + ", ".join(ajenas) + ". Usa un "
                "PostgreSQL exclusivo para pruebas (ver tests/postgres_auth/conftest.py)."
            )
    return ADMIN_URL


def _habilitar_login(base: str) -> None:
    """Como scripts/configurar_roles_locales.py: LOGIN con contraseÃ±a para los roles."""
    with admin(base) as conn:
        for rol, clave in CLAVES.items():
            conn.execute(f"ALTER ROLE {rol} LOGIN PASSWORD '{clave}'")


def sembrar(base: str) -> dict:
    hash_ok = contrasenas.hashear(CONTRASENA)
    with admin(base) as conn:
        roles = dict(conn.execute("SELECT nombre, id_rol FROM rol").fetchall())
        empresas = {}
        for clave, ruc in (("A", "1790016919001"), ("B", "0992339411001")):
            empresas[clave] = conn.execute(
                "INSERT INTO empresa (razon_social, ruc, correo_electronico) "
                "VALUES (%s, %s, %s) RETURNING id_empresa",
                (f"Empresa {clave}", ruc, f"{clave.lower()}@iondu.test"),
            ).fetchone()[0]
        for usuario, correo in CORREOS.items():
            conn.execute(
                "INSERT INTO usuario (id, email, password_hash, activo) VALUES (%s, %s, %s, %s)",
                (usuario, correo, hash_ok, usuario != INACTIVO),
            )
        miembros = (
            (ANA, "A", "Administrador", "Ana"),
            (OSCAR, "A", "Operativo", "Oscar"),
            (INACTIVO, "A", "Operativo", "Ines"),
            (MULTI, "A", "Operativo", "Multi"),
            (MULTI, "B", "Operativo", "Multi"),
            (BETO, "B", "Administrador", "Beto"),
        )
        for usuario, empresa, rol, nombre in miembros:
            conn.execute(
                "INSERT INTO usuario_empresa (id_usuario, id_empresa, id_rol, nombre_visible) "
                "VALUES (%s, %s, %s, %s)",
                (usuario, empresas[empresa], roles[rol], nombre),
            )
        for clave in ("A", "B"):
            cat = conn.execute(
                "INSERT INTO categoria_producto (id_empresa, nombre) VALUES (%s, 'General') "
                "RETURNING id_categoria_producto",
                (empresas[clave],),
            ).fetchone()[0]
            conn.execute(
                "INSERT INTO producto (id_empresa, id_categoria_producto, codigo_principal, "
                "nombre) VALUES (%s, %s, %s, 'CafÃ©')",
                (empresas[clave], cat, f"CAF-{clave}"),
            )
    return empresas


@pytest.fixture(scope="session")
def base(cluster):
    """Base creada con `alembic upgrade head`, con datos de dos empresas."""
    nombre = f"{PREFIJO}principal"
    crear_base(nombre)
    migrar(nombre, "upgrade", "head")
    _habilitar_login(nombre)
    empresas = sembrar(nombre)
    yield {"nombre": nombre, "empresas": empresas}
    borrar_base(nombre)
