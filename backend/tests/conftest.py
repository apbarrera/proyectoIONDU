"""Piezas comunes de las pruebas.

Las pruebas que usan la base de datos necesitan TEST_DATABASE_URL apuntando a una
base cuyo nombre termine en "_test" (se borran y crean sus tablas). Sin esa
variable se saltan; las demás corren igual.

    TEST_DATABASE_URL=postgresql+psycopg://iondu:<clave>@127.0.0.1:15432/iondu_test
"""

import os

# Las pruebas simulan el entorno de desarrollo (encabezado X-Empresa-Id habilitado).
os.environ["APP_ENV"] = "development"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Empresa  # noqa: E402

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


@pytest.fixture(scope="session")
def engine():
    if not TEST_DATABASE_URL:
        pytest.skip("Define TEST_DATABASE_URL para las pruebas con base de datos")
    if not (make_url(TEST_DATABASE_URL).database or "").endswith("_test"):
        pytest.fail("TEST_DATABASE_URL debe apuntar a una base cuyo nombre termine en _test")
    eng = create_engine(TEST_DATABASE_URL, connect_args={"connect_timeout": 5})
    try:
        eng.connect().close()
    except OperationalError:
        pytest.exit(
            "No se pudo conectar a TEST_DATABASE_URL. ¿Está encendido Docker con el servicio db?",
            returncode=1,
        )

    # Esquema mínimo para representar la dependencia externa de Supabase Auth.
    # Se crea únicamente en la base de pruebas.
    with eng.begin() as conn:
        conn.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS auth")

    Base.metadata.drop_all(eng)
    # Imita el esquema "auth" de Supabase (auth.users), al que apuntan algunos modelos;
    # un PostgreSQL normal (Docker local, CI) no lo tiene.
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
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
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def empresas(db) -> tuple[int, int]:
    """Dos empresas para probar el aislamiento: (id_a, id_b)."""
    a = Empresa(razon_social="Empresa A", ruc="0990000000001", correo_electronico="a@test.ec")
    b = Empresa(razon_social="Empresa B", ruc="0990000000002", correo_electronico="b@test.ec")
    db.add_all([a, b])
    db.flush()
    return a.id_empresa, b.id_empresa
