"""Clase base de todos los modelos (tablas) de SQLAlchemy.

Todo modelo hereda de `Base`; así queda registrado en `Base.metadata`, que es
lo que Alembic compara contra la base de datos para generar migraciones.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Nombres de restricciones e índices fijos y predecibles (mismo estilo que
# PostgreSQL y que database/schema.sql). Sin esto, Alembic no puede modificar
# ni borrar una restricción en una migración posterior.
NAMING_CONVENTION = {
    "pk": "%(table_name)s_pkey",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "uq": "%(table_name)s_%(column_0_N_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
