"""Conexión PostgreSQL independiente para el worker."""

from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import TIMEZONE, get_settings


class WorkerSession(Session):
    """Sesión técnica independiente de las sesiones de la API."""


@lru_cache
def get_worker_engine() -> Engine:
    """Crea el engine exclusivo del worker, sin fallback a DATABASE_URL."""
    url = get_settings().worker_database_url

    if not url:
        raise RuntimeError(
            "WORKER_DATABASE_URL no está configurada. "
            "El worker no utilizará DATABASE_URL como alternativa."
        )

    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=2,
        connect_args={
            "options": f"-c timezone={TIMEZONE}",
            "connect_timeout": 5,
        },
    )


@lru_cache
def get_worker_session_factory() -> sessionmaker[WorkerSession]:
    """Devuelve la fábrica de sesiones exclusiva del worker."""
    return sessionmaker(
        bind=get_worker_engine(),
        class_=WorkerSession,
        autoflush=False,
        expire_on_commit=False,
    )


@contextmanager
def bloqueo_factura(
    empresa_id: int,
    factura_id: int,
    *,
    engine: Engine | None = None,
):
    """
    Mantiene un advisory lock de sesión durante el procesamiento.

    La conexión queda reservada hasta liberar el bloqueo. Las operaciones
    de negocio deben realizarse mediante sesiones independientes y
    transacciones cortas.

    El parámetro engine permite probar el mecanismo con iondu_test.
    """
    if empresa_id <= 0 or factura_id <= 0:
        raise ValueError("Los identificadores del bloqueo deben ser positivos.")

    motor = engine if engine is not None else get_worker_engine()

    with motor.connect() as conexion:
        with conexion.begin():
            adquirido = conexion.scalar(
                select(
                    func.pg_try_advisory_lock(
                        empresa_id,
                        factura_id,
                    )
                )
            )

        if not adquirido:
            yield False
            return

        try:
            yield True
        finally:
            try:
                with conexion.begin():
                    liberado = conexion.scalar(
                        select(
                            func.pg_advisory_unlock(
                                empresa_id,
                                factura_id,
                            )
                        )
                    )

                if not liberado:
                    raise RuntimeError(
                        "PostgreSQL no confirmó la liberación "
                        "del bloqueo de la factura."
                    )
            except Exception:
                # No devolver al pool una conexión cuyo estado de bloqueo
                # no podamos garantizar.
                try:
                    conexion.invalidate()
                except Exception:
                    pass
                raise


def dispose_worker_engine() -> None:
    """Cierra el pool y limpia las fábricas cacheadas del worker."""
    engine = get_worker_engine()
    engine.dispose()
    get_worker_session_factory.cache_clear()
    get_worker_engine.cache_clear()
