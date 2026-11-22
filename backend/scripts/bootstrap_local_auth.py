"""Inicializa el esquema auth m?nimo para desarrollo local.

No sustituye Supabase Auth. No debe ejecutarse en producci?n.
Solo permite crear auth.users(id UUID) en localhost, base iondu.
"""

import sys
from pathlib import Path

# Permite importar app cuando el script se ejecuta directamente.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.core.config import get_settings


def main() -> None:
    url = make_url(get_settings().database_url)

    # Protecci?n estricta: no ejecutar contra Supabase ni otra base.
    if (
        url.get_backend_name() != "postgresql"
        or url.host not in {"localhost", "127.0.0.1", "::1"}
        or url.database != "iondu"
    ):
        raise SystemExit(
            "ABORTADO: este script solo puede ejecutarse contra "
            "PostgreSQL local (localhost) y la base iondu."
        )

    engine = create_engine(url)

    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS auth.users (
                        id UUID PRIMARY KEY
                    )
                    """
                )
            )

            column = connection.execute(
                text(
                    """
                    SELECT data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'auth'
                      AND table_name = 'users'
                      AND column_name = 'id'
                    """
                )
            ).one_or_none()

            if column is None or column.data_type != "uuid" or column.is_nullable != "NO":
                raise RuntimeError(
                    "auth.users existe, pero su columna id no tiene "
                    "la estructura UUID NOT NULL esperada. "
                    "No se modific? la tabla existente."
                )

        print("OK: esquema auth local disponible y auth.users.id es UUID NOT NULL.")
        print("Nota: esta tabla auxiliar no implementa autenticaci?n ni reemplaza Supabase Auth.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
