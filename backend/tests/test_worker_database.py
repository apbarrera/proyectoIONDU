import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.db.session import APISession, _aplicar_contexto_rls
from app.worker import database


@pytest.fixture(autouse=True)
def limpiar_cache():
    database.get_worker_session_factory.cache_clear()
    database.get_worker_engine.cache_clear()
    yield
    database.get_worker_session_factory.cache_clear()
    database.get_worker_engine.cache_clear()


def test_worker_exige_su_propia_url_sin_fallback(monkeypatch):
    monkeypatch.setattr(
        database,
        "get_settings",
        lambda: Settings(
            database_url="postgresql+psycopg://api:fake@localhost/iondu",
            worker_database_url=None,
        ),
    )

    with pytest.raises(RuntimeError, match="WORKER_DATABASE_URL"):
        database.get_worker_engine()


def test_worker_engine_utiliza_exclusivamente_worker_database_url(monkeypatch):
    url_worker = "postgresql+psycopg://worker:fake@localhost/iondu"

    monkeypatch.setattr(
        database,
        "get_settings",
        lambda: Settings(
            database_url="postgresql+psycopg://api:fake@localhost/iondu",
            worker_database_url=url_worker,
        ),
    )

    llamadas = []
    engine_falso = object()

    def crear_engine(url, **kwargs):
        llamadas.append((url, kwargs))
        return engine_falso

    monkeypatch.setattr(database, "create_engine", crear_engine)

    resultado = database.get_worker_engine()

    assert resultado is engine_falso
    assert len(llamadas) == 1
    assert llamadas[0][0] == url_worker
    assert llamadas[0][1]["pool_size"] == 3
    assert llamadas[0][1]["max_overflow"] == 2


def test_worker_session_factory_usa_worker_session(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")

    monkeypatch.setattr(
        database,
        "get_worker_engine",
        lambda: engine,
    )

    factory = database.get_worker_session_factory()

    assert issubclass(factory.class_, database.WorkerSession)
    assert factory.kw["bind"] is engine
    assert factory.kw["autoflush"] is False
    assert factory.kw["expire_on_commit"] is False

    engine.dispose()


def test_worker_no_ejecuta_listener_rls_de_la_api():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    try:
        factory = sessionmaker_for_test(engine, database.WorkerSession)

        with factory() as session:
            resultado = session.execute(text("SELECT 1")).scalar_one()

        assert resultado == 1
    finally:
        engine.dispose()


def test_api_session_conserva_listener_rls():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    try:
        factory = sessionmaker_for_test(engine, APISession)

        with pytest.raises(OperationalError, match="set_config"), factory() as session:
            session.execute(text("SELECT 1"))
    finally:
        engine.dispose()


def sessionmaker_for_test(engine, session_class):
    from sqlalchemy.orm import sessionmaker

    return sessionmaker(
        bind=engine,
        class_=session_class,
        autoflush=False,
        expire_on_commit=False,
    )


def test_listener_rls_registrado_solo_en_api_session():
    from sqlalchemy import event

    assert event.contains(APISession, "after_begin", _aplicar_contexto_rls)
    assert not event.contains(
        database.WorkerSession,
        "after_begin",
        _aplicar_contexto_rls,
    )


def test_bloqueo_factura_impide_adquisicion_simultanea(engine):
    from app.worker.database import bloqueo_factura

    with bloqueo_factura(7, 15, engine=engine) as adquirido:
        assert adquirido is True

        with bloqueo_factura(7, 15, engine=engine) as segundo:
            assert segundo is False

    # Una vez terminado el primer contexto, debe poder adquirirse otra vez.
    with bloqueo_factura(7, 15, engine=engine) as tercero:
        assert tercero is True


def test_bloqueo_factura_se_libera_ante_excepcion(engine):
    from app.worker.database import bloqueo_factura

    with (
        pytest.raises(RuntimeError, match="fallo simulado"),
        bloqueo_factura(7, 16, engine=engine) as adquirido,
    ):
        assert adquirido is True
        raise RuntimeError("fallo simulado")

    # La excepción no debe dejar el bloqueo retenido.
    with bloqueo_factura(7, 16, engine=engine) as siguiente:
        assert siguiente is True


def test_bloqueo_factura_rechaza_identificadores_invalidos():
    from app.worker.database import bloqueo_factura

    with pytest.raises(ValueError), bloqueo_factura(0, 15):
        pass

    with pytest.raises(ValueError), bloqueo_factura(7, 0):
        pass
