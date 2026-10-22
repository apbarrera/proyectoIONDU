"""Conexión a PostgreSQL (Supabase en producción, el contenedor "db" en local).

- `get_engine()` crea UNA sola conexión compartida (con su pool) la primera vez
  que se necesita; si DATABASE_URL no está definida, devuelve None.
- `get_db()` es la dependencia de FastAPI que entrega una sesión por petición
  y la cierra al terminar, pase lo que pase.
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import TIMEZONE, get_settings


@lru_cache
def get_engine() -> Engine | None:
    url = get_settings().database_url
    if not url:
        return None
    return create_engine(
        url,
        # Descarta conexiones que el pooler de Supabase haya cerrado.
        pool_pre_ping=True,
        # Pool pequeño: el Session Pooler de Supabase limita las conexiones,
        # y la API corre con 2 workers de uvicorn (cada uno tiene su pool).
        pool_size=5,
        max_overflow=5,
        # Cada conexión trabaja con la hora de Ecuador; si la base no
        # responde en 5 s, se falla rápido en vez de colgar la petición.
        connect_args={"options": f"-c timezone={TIMEZONE}", "connect_timeout": 5},
    )


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    engine = get_engine()
    if engine is None:
        raise RuntimeError("DATABASE_URL no está configurada")
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Uso en un endpoint: `def listar(db: Session = Depends(get_db))`."""
    with _session_factory()() as session:
        yield session


def database_status() -> str:
    """'ok', 'error' o 'not_configured'. Lo usa /api/health."""
    engine = get_engine()
    if engine is None:
        return "not_configured"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"
