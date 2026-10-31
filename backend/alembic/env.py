"""Entorno de Alembic: cómo se conecta a la base y qué modelos conoce.

La dirección de la base sale de DATABASE_URL (la misma configuración que usa
la API), nunca de alembic.ini.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import app.models  # noqa: F401  (registra todos los modelos en Base.metadata)
from app.core.config import get_settings
from app.db.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    url = get_settings().database_url
    if not url:
        raise RuntimeError("Define DATABASE_URL para ejecutar las migraciones")
    return url


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    # No gestionar tablas del esquema auth de Supabase.
    if type_ == "table" and getattr(obj, "schema", None) == "auth":
        return False

    # Una tabla que existe en la base pero no tiene modelo NO se propone borrar:
    # el autogenerate solo crea o modifica; un DROP TABLE se escribe a mano.
    return not (type_ == "table" and reflected and compare_to is None)


def run_migrations_offline() -> None:
    """Genera el SQL sin conectarse (alembic upgrade head --sql)."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Aplica las migraciones conectándose a la base."""
    engine = create_engine(_database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
