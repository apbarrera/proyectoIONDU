"""Conexión PostgreSQL independiente para el worker."""

from functools import lru_cache

from sqlalchemy import Engine, create_engine
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


def dispose_worker_engine() -> None:
    """Cierra el pool y limpia las fábricas cacheadas del worker."""
    engine = get_worker_engine()
    engine.dispose()
    get_worker_session_factory.cache_clear()
    get_worker_engine.cache_clear()
