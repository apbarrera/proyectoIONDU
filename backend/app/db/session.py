"""Conexión a PostgreSQL y contexto transaccional de seguridad RLS."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import TIMEZONE, get_settings

# Claves privadas utilizadas para conservar el contexto entre transacciones.
_RLS_USER_KEY = "rls_usuario_id"
_RLS_COMPANY_KEY = "rls_empresa_id"


def _aplicar_contexto_rls(session, transaction, connection) -> None:
    """Aplica el contexto RLS al iniciar cada transacción de la sesión."""
    connection.execute(
        text("""
            SELECT
                set_config(
                    'app.current_user_id',
                    :usuario_id,
                    true
                ),
                set_config(
                    'app.current_empresa_id',
                    :empresa_id,
                    true
                )
        """),
        {
            "usuario_id": session.info.get(_RLS_USER_KEY) or "",
            "empresa_id": (
                str(session.info[_RLS_COMPANY_KEY])
                if session.info.get(_RLS_COMPANY_KEY) is not None
                else ""
            ),
        },
    )


class APISession(Session):
    """Sesión de la API con contexto transaccional RLS."""


# El listener se registra exclusivamente en las sesiones de la API.
# WorkerSession hereda directamente de Session y no recibe este evento.
event.listen(APISession, "after_begin", _aplicar_contexto_rls)


def establecer_contexto_rls(
    session: Session,
    *,
    usuario_id: str | None,
    empresa_id: int | None,
) -> None:
    """Actualiza el contexto RLS de la transacción actual y las siguientes."""
    session.info[_RLS_USER_KEY] = str(usuario_id) if usuario_id else None
    session.info[_RLS_COMPANY_KEY] = empresa_id

    # Actualiza también la transacción que ya pudiera estar abierta.
    session.execute(
        text("""
            SELECT
                set_config(
                    'app.current_user_id',
                    :usuario_id,
                    true
                ),
                set_config(
                    'app.current_empresa_id',
                    :empresa_id,
                    true
                )
        """),
        {
            "usuario_id": session.info[_RLS_USER_KEY] or "",
            "empresa_id": (str(empresa_id) if empresa_id is not None else ""),
        },
    )


# Claves privadas utilizadas para conservar el contexto entre transacciones.
_RLS_USER_KEY = "rls_usuario_id"
_RLS_COMPANY_KEY = "rls_empresa_id"


def _aplicar_contexto_rls(session, transaction, connection) -> None:
    """Aplica el contexto RLS al iniciar cada transacción de la sesión."""
    connection.execute(
        text("""
            SELECT
                set_config(
                    'app.current_user_id',
                    :usuario_id,
                    true
                ),
                set_config(
                    'app.current_empresa_id',
                    :empresa_id,
                    true
                )
        """),
        {
            "usuario_id": session.info.get(_RLS_USER_KEY) or "",
            "empresa_id": (
                str(session.info[_RLS_COMPANY_KEY])
                if session.info.get(_RLS_COMPANY_KEY) is not None
                else ""
            ),
        },
    )


class APISession(Session):
    """Sesión de la API con contexto transaccional RLS."""


# El listener se registra exclusivamente en las sesiones de la API.
# WorkerSession hereda directamente de Session y no recibe este evento.
event.listen(APISession, "after_begin", _aplicar_contexto_rls)


def establecer_contexto_rls(
    session: Session,
    *,
    usuario_id: str | None,
    empresa_id: int | None,
) -> None:
    """Actualiza el contexto RLS de la transacción actual y las siguientes."""
    session.info[_RLS_USER_KEY] = str(usuario_id) if usuario_id else None
    session.info[_RLS_COMPANY_KEY] = empresa_id

    # Actualiza también la transacción que ya pudiera estar abierta.
    session.execute(
        text("""
            SELECT
                set_config(
                    'app.current_user_id',
                    :usuario_id,
                    true
                ),
                set_config(
                    'app.current_empresa_id',
                    :empresa_id,
                    true
                )
        """),
        {
            "usuario_id": session.info[_RLS_USER_KEY] or "",
            "empresa_id": (
                str(empresa_id) if empresa_id is not None else ""
            ),
        },
    )


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
        connect_args={
            "options": f"-c timezone={TIMEZONE}",
            "connect_timeout": 5,
        },
    )


@lru_cache
def _session_factory() -> sessionmaker[APISession]:
    return sessionmaker(
        bind=get_engine(),
        class_=APISession,
        autoflush=False,
        expire_on_commit=False,
    )


def get_db() -> Iterator[Session]:
    """Entrega una sesión por petición y la cierra al terminar."""
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
