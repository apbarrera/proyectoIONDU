"""Habilita en la base LOCAL los roles de ejecución con la contraseña del .env.

En producción la API se conecta como iondu_app y el worker como iondu_worker: sin
privilegios de administrador y sujetos a RLS. Para que en local pase lo mismo (y los
errores de permisos aparezcan aquí y no en producción), este script les da LOGIN
con la contraseña que traen DATABASE_URL y WORKER_DATABASE_URL.

Los roles los crea la migración b72e91c4a630; correrlo después de `alembic upgrade head`.
Usa MIGRATION_DATABASE_URL (el usuario iondu, administrador de la base local).

Uso, con Docker encendido:
    docker compose run --rm --no-deps api python -m scripts.configurar_roles_locales
"""

import sys

from psycopg import sql
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from app.core.config import get_settings

SERVIDORES_LOCALES = {"127.0.0.1", "localhost", "db"}
ROLES_DE_EJECUCION = {"iondu_app", "iondu_worker"}


def main() -> None:
    settings = get_settings()
    if not settings.migration_database_url:
        sys.exit("Define MIGRATION_DATABASE_URL (usuario administrador de la base local).")
    admin = make_url(settings.migration_database_url)
    if admin.host not in SERVIDORES_LOCALES or admin.database != "iondu":
        sys.exit("Solo se usa con la base local iondu.")

    credenciales = {}
    for nombre, url in (
        ("DATABASE_URL", settings.database_url),
        ("WORKER_DATABASE_URL", settings.worker_database_url),
    ):
        destino = make_url(url) if url else None
        if destino is None or destino.username not in ROLES_DE_EJECUCION:
            sys.exit(f"{nombre} debe usar el usuario iondu_app o iondu_worker (ver .env.example).")
        if not destino.password:
            sys.exit(f"{nombre} no tiene contraseña.")
        credenciales[destino.username] = destino.password

    engine = create_engine(admin)
    try:
        with engine.begin() as conn:
            cursor = conn.connection.cursor()
            for rol, contrasena in credenciales.items():
                cursor.execute(
                    sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(
                        sql.Identifier(rol), sql.Literal(contrasena)
                    )
                )
                print(f"{rol}: LOGIN habilitado.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
