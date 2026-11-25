"""Instalador inicial del esquema IONDU para pruebas locales.

Destino exclusivo: iondu_fresh_install_test.
No ejecuta migraciones ni elimina objetos.

Para crear el esquema de prueba local, exige --crear-auth-shim-local.
Ese marcador de auth.users es solo para pruebas; no sustituye Supabase Auth.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
TARGET_DATABASE = "iondu_fresh_install_test"

sys.path.insert(0, str(BACKEND_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--crear-auth-shim-local",
        action="store_true",
        help="Crear auth.users mínimo para pruebas locales; nunca para producción.",
    )
    args = parser.parse_args()

    config = dotenv_values(PROJECT_ROOT / ".env")
    configured_url = config.get("DATABASE_URL")
    if not configured_url:
        raise SystemExit("ERROR: DATABASE_URL no está definida en el .env de la raíz.")

    base_url = make_url(configured_url)
    if base_url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit("ERROR: solo se admite PostgreSQL local.")
    if base_url.database != "modelobd_iondu":
        raise SystemExit(
            "ERROR: DATABASE_URL no apunta a modelobd_iondu. "
            "Revisa la configuración antes de continuar."
        )
    if not args.crear_auth_shim_local:
        raise SystemExit(
            "Instalación cancelada sin cambios. Para una instalación local de prueba, "
            "revisa el código y vuelve a ejecutar con --crear-auth-shim-local. "
            "Este modo no es válido para producción."
        )

    from app import models  # noqa: F401
    from app.db.base import Base

    business_tables = [
        table
        for table in Base.metadata.sorted_tables
        if table.schema in (None, "public") and table.name != "users"
    ]
    if len(business_tables) != 17:
        raise SystemExit(
            f"ERROR: se esperaban 17 tablas de negocio; se encontraron "
            f"{len(business_tables)}. No se ha conectado a la base."
        )

    target_url = base_url.set(database=TARGET_DATABASE)
    engine = create_engine(
        target_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )

    try:
        with engine.begin() as conn:
            current_db = conn.execute(text("SELECT current_database()")).scalar_one()
            if current_db != TARGET_DATABASE:
                raise RuntimeError("La conexión no apunta a la base autorizada.")

            existing_objects = conn.execute(
                text("""
                    SELECT n.nspname, c.relname, c.relkind
                    FROM pg_class AS c
                    JOIN pg_namespace AS n ON n.oid = c.relnamespace
                    WHERE n.nspname IN ('public', 'auth')
                      AND c.relkind IN ('r', 'p', 'S', 'v', 'm', 'f')
                      AND c.relname NOT LIKE 'pg_%'
                    ORDER BY n.nspname, c.relname
                """)
            ).all()

            if existing_objects:
                raise RuntimeError(
                    "Instalación cancelada: public o auth contienen objetos. "
                    "No se ha intentado crear ninguna tabla."
                )

            conn.execute(text("CREATE SCHEMA IF NOT EXISTS public"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))

            # Marcador mínimo solo para pruebas locales.
            conn.execute(
                text("""
                CREATE TABLE auth.users (
                    id UUID PRIMARY KEY
                )
            """)
            )

            # La FK de usuario_empresa apunta al marcador auth.users.
            # Solo se pasan las 17 tablas de negocio a create_all.
            Base.metadata.create_all(conn, tables=business_tables)

            actual = conn.execute(
                text("""
                    SELECT n.nspname, c.relname
                    FROM pg_class AS c
                    JOIN pg_namespace AS n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'public'
                      AND c.relkind IN ('r', 'p')
                      AND c.relname NOT LIKE 'pg_%'
                    ORDER BY c.relname
                """)
            ).all()

            if len(actual) != 17:
                raise RuntimeError(
                    f"Verificación fallida: se esperaban 17 tablas en public "
                    f"y se encontraron {len(actual)}."
                )

        print("Creación inicial de tablas completada.")
        print(f"Base: {TARGET_DATABASE}")
        print(f"Tablas de negocio en public: {len(actual)}")
        print("auth.users: marcador mínimo de pruebas locales.")
        print("Pendiente: verificar funciones, triggers, RLS y permisos.")
        print("No se ejecutaron migraciones.")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
