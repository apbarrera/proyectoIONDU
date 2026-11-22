"""Piezas comunes de las pruebas.

Las pruebas que usan la base de datos necesitan TEST_DATABASE_URL apuntando a una
base cuyo nombre termine en "_test" (se borran y crean sus tablas). Sin esa
variable se saltan; las demás corren igual.

    TEST_DATABASE_URL=postgresql+psycopg://iondu:<clave>@127.0.0.1:15432/iondu_test
"""

import os
import warnings

# Las pruebas simulan el entorno de desarrollo (encabezado X-Empresa-Id habilitado).
os.environ["APP_ENV"] = "development"
os.environ["DEV_USER_ID"] = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

import uuid  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.api.deps import get_verificador  # noqa: E402
from app.db.base import Base, auth_users  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Empresa, Rol, UsuarioEmpresa  # noqa: E402
from app.models.rol import ADMINISTRADOR, OPERATIVO  # noqa: E402
from tests.tokens import crear_token, verificador_de_prueba  # noqa: E402

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
SERVIDORES_DE_PRUEBA = {"127.0.0.1", "localhost", "db"}


def validar_url_pruebas(database_url: str) -> None:
    """Impide que las pruebas destructivas apunten a una base distinta de iondu_test."""
    try:
        url = make_url(database_url)
    except Exception:
        pytest.fail("TEST_DATABASE_URL no contiene una URL válida")

    if url.drivername != "postgresql+psycopg":
        pytest.fail("TEST_DATABASE_URL debe usar postgresql+psycopg")
    if url.database != "iondu_test":
        pytest.fail("TEST_DATABASE_URL debe apuntar exactamente a iondu_test")
    # Solo servidores locales: tu Docker (127.0.0.1:15432), el contenedor "db" (Docker
    # Compose) o el PostgreSQL temporal del CI (127.0.0.1:5432). Nunca Supabase.
    if url.host not in SERVIDORES_DE_PRUEBA:
        pytest.fail(
            "TEST_DATABASE_URL debe apuntar a un PostgreSQL local "
            f"({', '.join(sorted(SERVIDORES_DE_PRUEBA))})"
        )
    if url.username != "iondu":
        pytest.fail("TEST_DATABASE_URL debe conectarse con el usuario iondu")


@pytest.fixture(scope="session")
def engine():
    if not TEST_DATABASE_URL:
        pytest.skip("Define TEST_DATABASE_URL para las pruebas con base de datos")

    validar_url_pruebas(TEST_DATABASE_URL)
    eng = create_engine(TEST_DATABASE_URL, connect_args={"connect_timeout": 5})
    inicializado = False

    try:
        try:
            with eng.connect() as conn:
                identidad = conn.exec_driver_sql(
                    """
                    SELECT current_database(), current_user,
                           rol.rolsuper, rol.rolbypassrls
                    FROM pg_roles AS rol
                    WHERE rol.rolname = current_user
                    """
                ).one()

                if identidad[0] != "iondu_test" or identidad[1] != "iondu":
                    pytest.fail("La conexión real no corresponde a iondu_test con el usuario iondu")

                if identidad[2] or identidad[3]:
                    warnings.warn(
                        "El usuario de pruebas tiene permisos SUPERUSER o BYPASSRLS; "
                        "estas pruebas no pueden demostrar el cumplimiento de RLS "
                        "a nivel de PostgreSQL.",
                        RuntimeWarning,
                        stacklevel=2,
                    )
        except OperationalError:
            pytest.exit(
                "No se pudo conectar a iondu_test. ¿Está encendido Docker con el servicio db?",
                returncode=1,
            )

        # Esquema mínimo para representar la dependencia externa de Supabase Auth.
        with eng.begin() as conn:
            conn.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS auth")

        Base.metadata.drop_all(eng)
        # Imita el esquema auth.users de Supabase en la base de pruebas.
        Base.metadata.create_all(eng)
        inicializado = True
        yield eng
    finally:
        try:
            if inicializado:
                Base.metadata.drop_all(eng)
        finally:
            eng.dispose()


@pytest.fixture
def db(engine):
    """Sesión dentro de una transacción que se deshace al terminar cada prueba.
    Los commit() del código se vuelven puntos intermedios (savepoints)."""
    with engine.connect() as conn:
        transaccion = conn.begin()
        session = Session(bind=conn, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            transaccion.rollback()


@pytest.fixture
def client(db):
    def sesion_por_peticion():
        session = Session(
            bind=db.connection(),
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = sesion_por_peticion
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def empresas(db, roles) -> tuple[int, int]:
    """Dos empresas aisladas y un usuario demo con membres?a expl?cita en ambas."""
    a = Empresa(razon_social="Empresa A", ruc="0990000000001", correo_electronico="a@test.ec")
    b = Empresa(razon_social="Empresa B", ruc="0990000000002", correo_electronico="b@test.ec")
    db.add_all([a, b])
    db.flush()

    usuario_demo = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    db.execute(auth_users.insert().values(id=usuario_demo))
    db.add_all(
        [
            UsuarioEmpresa(
                id_usuario=usuario_demo,
                id_empresa=empresa.id_empresa,
                id_rol=roles[ADMINISTRADOR],
                nombre_visible="Usuario Demo",
                estado="ACTIVO",
            )
            for empresa in (a, b)
        ]
    )
    db.flush()
    return a.id_empresa, b.id_empresa


# ---------- Usuarios con sesión (token de un "Supabase falso", ver tests/tokens.py) ----------
@pytest.fixture
def supabase_falso():
    """La API verifica los tokens con la llave de prueba en vez de la de Supabase."""
    app.dependency_overrides[get_verificador] = verificador_de_prueba
    yield
    app.dependency_overrides.pop(get_verificador, None)


@pytest.fixture
def roles(db) -> dict[str, int]:
    admin, operativo = Rol(nombre=ADMINISTRADOR), Rol(nombre=OPERATIVO)
    db.add_all([admin, operativo])
    db.flush()
    return {ADMINISTRADOR: admin.id_rol, OPERATIVO: operativo.id_rol}


@pytest.fixture
def agregar_pertenencia(db, roles):
    """Agrega una pertenencia de un usuario existente a una empresa."""

    def agregar(
        usuario: uuid.UUID, id_empresa: int, rol: str = ADMINISTRADOR, estado: str = "ACTIVO"
    ) -> None:
        db.add(
            UsuarioEmpresa(
                id_usuario=usuario,
                id_empresa=id_empresa,
                id_rol=roles[rol],
                nombre_visible="Ana Torres",
                estado=estado,
            )
        )
        db.flush()

    return agregar


@pytest.fixture
def nuevo_usuario(db, agregar_pertenencia):
    """Crea un usuario de Supabase (auth.users) con pertenencia a una empresa."""

    def crear(id_empresa: int, rol: str = ADMINISTRADOR, estado: str = "ACTIVO") -> uuid.UUID:
        usuario = uuid.uuid4()
        db.execute(auth_users.insert().values(id=usuario))
        agregar_pertenencia(usuario, id_empresa, rol, estado)
        return usuario

    return crear


def con_token(usuario: uuid.UUID, **extra: str) -> dict[str, str]:
    """Encabezados de una petición con la sesión de ese usuario."""
    return {"Authorization": f"Bearer {crear_token(usuario)}"} | extra


@pytest.fixture
def usuarios_empresa(empresas, nuevo_usuario):
    """Un usuario autenticado con pertenencia activa para cada empresa de prueba."""
    a, b = empresas
    return {a: nuevo_usuario(a), b: nuevo_usuario(b)}
