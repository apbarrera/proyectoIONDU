"""Instala funciones y triggers de integridad en la base local de prueba.

Destino exclusivo: iondu_fresh_install_test.
No modifica tablas, políticas RLS, auth.uid() ni migraciones.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
TARGET_DATABASE = "iondu_fresh_install_test"

sys.path.insert(0, str(BACKEND_ROOT))

FUNCTIONS = {
    "validar_detalle_venta_empresa": """
CREATE OR REPLACE FUNCTION public.validar_detalle_venta_empresa()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    empresa_venta integer;
    empresa_producto integer;
BEGIN
    SELECT v.id_empresa
      INTO empresa_venta
      FROM public.venta AS v
     WHERE v.id_venta = NEW.id_venta;

    IF empresa_venta IS NULL THEN
        RAISE EXCEPTION 'La venta % no existe', NEW.id_venta;
    END IF;

    IF NEW.id_producto IS NOT NULL THEN
        SELECT p.id_empresa
          INTO empresa_producto
          FROM public.producto AS p
         WHERE p.id_producto = NEW.id_producto;

        IF empresa_producto IS NULL
           OR empresa_producto <> empresa_venta THEN
            RAISE EXCEPTION
                'El producto debe pertenecer a la misma empresa que la venta';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;
""",
    "validar_membresia_activa": """
CREATE OR REPLACE FUNCTION public.validar_membresia_activa()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.id_usuario IS NOT NULL
       AND NOT EXISTS (
            SELECT 1
              FROM public.usuario_empresa AS ue
             WHERE ue.id_usuario = NEW.id_usuario
               AND ue.id_empresa = NEW.id_empresa
               AND ue.estado = 'ACTIVO'
       )
    THEN
        RAISE EXCEPTION
            'El usuario no tiene membresia activa en la empresa %',
            NEW.id_empresa;
    END IF;

    RETURN NEW;
END;
$$;
""",
    "validar_movimiento_inventario_empresa": """
CREATE OR REPLACE FUNCTION public.validar_movimiento_inventario_empresa()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    empresa_producto integer;
BEGIN
    SELECT p.id_empresa
      INTO empresa_producto
      FROM public.producto AS p
     WHERE p.id_producto = NEW.id_producto;

    IF empresa_producto IS NULL THEN
        RAISE EXCEPTION 'El producto no existe';
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM public.usuario_empresa AS ue
         WHERE ue.id_usuario = NEW.id_usuario
           AND ue.id_empresa = empresa_producto
           AND ue.estado = 'ACTIVO'
    ) THEN
        RAISE EXCEPTION
            'El usuario debe tener membresia activa en la empresa del producto';
    END IF;

    RETURN NEW;
END;
$$;
""",
}

TRIGGERS = {
    "trg_accion_ia_membresia_activa": """
CREATE TRIGGER trg_accion_ia_membresia_activa
BEFORE INSERT OR UPDATE OF id_usuario, id_empresa
ON public.accion_ia
FOR EACH ROW
WHEN (NEW.id_usuario IS NOT NULL)
EXECUTE FUNCTION public.validar_membresia_activa();
""",
    "trg_gasto_membresia_activa": """
CREATE TRIGGER trg_gasto_membresia_activa
BEFORE INSERT OR UPDATE OF id_usuario, id_empresa
ON public.gasto
FOR EACH ROW
EXECUTE FUNCTION public.validar_membresia_activa();
""",
    "trg_validar_detalle_venta_empresa": """
CREATE TRIGGER trg_validar_detalle_venta_empresa
BEFORE INSERT OR UPDATE OF id_venta, id_producto
ON public.detalle_venta
FOR EACH ROW
EXECUTE FUNCTION public.validar_detalle_venta_empresa();
""",
    "trg_validar_movimiento_inventario_empresa": """
CREATE TRIGGER trg_validar_movimiento_inventario_empresa
BEFORE INSERT OR UPDATE OF id_producto, id_usuario
ON public.movimiento_inventario
FOR EACH ROW
EXECUTE FUNCTION public.validar_movimiento_inventario_empresa();
""",
    "trg_venta_membresia_activa": """
CREATE TRIGGER trg_venta_membresia_activa
BEFORE INSERT OR UPDATE OF id_usuario, id_empresa
ON public.venta
FOR EACH ROW
EXECUTE FUNCTION public.validar_membresia_activa();
""",
}


def main() -> None:
    config = dotenv_values(PROJECT_ROOT / ".env")
    configured_url = config.get("DATABASE_URL")

    if not configured_url:
        raise SystemExit("ERROR: DATABASE_URL no está definida en el .env raíz.")

    base_url = make_url(configured_url)

    if base_url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit("ERROR: solo se admite PostgreSQL local.")

    if base_url.database != "modelobd_iondu":
        raise SystemExit(
            "ERROR: DATABASE_URL debe apuntar a modelobd_iondu "
            "para identificar la configuración local."
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

            table_count = conn.execute(
                text("""
                SELECT count(*)
                FROM pg_tables
                WHERE schemaname = 'public'
                  AND tablename NOT LIKE 'pg_%'
            """)
            ).scalar_one()

            if table_count != 17:
                raise RuntimeError(
                    f"Se esperaban 17 tablas de negocio; se encontraron {table_count}."
                )

            existing_triggers = (
                conn.execute(
                    text("""
                    SELECT t.tgname
                    FROM pg_trigger AS t
                    JOIN pg_class AS c ON c.oid = t.tgrelid
                    JOIN pg_namespace AS n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'public'
                      AND NOT t.tgisinternal
                      AND t.tgname = ANY(:names)
                """),
                    {"names": list(TRIGGERS)},
                )
                .scalars()
                .all()
            )

            if existing_triggers:
                raise RuntimeError(
                    "Instalación cancelada: ya existen triggers objetivo: "
                    + ", ".join(existing_triggers)
                )

            existing_functions = (
                conn.execute(
                    text("""
                    SELECT p.proname
                    FROM pg_proc AS p
                    JOIN pg_namespace AS n ON n.oid = p.pronamespace
                    WHERE n.nspname = 'public'
                      AND p.proname = ANY(:names)
                """),
                    {"names": list(FUNCTIONS)},
                )
                .scalars()
                .all()
            )

            if existing_functions:
                raise RuntimeError(
                    "Instalaci?n cancelada: ya existen funciones objetivo: "
                    + ", ".join(existing_functions)
                )

            for ddl in FUNCTIONS.values():
                conn.execute(text(ddl))

            for ddl in TRIGGERS.values():
                conn.execute(text(ddl))

            created = (
                conn.execute(
                    text("""
                    SELECT t.tgname
                    FROM pg_trigger AS t
                    JOIN pg_class AS c ON c.oid = t.tgrelid
                    JOIN pg_namespace AS n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'public'
                      AND NOT t.tgisinternal
                      AND t.tgname = ANY(:names)
                """),
                    {"names": list(TRIGGERS)},
                )
                .scalars()
                .all()
            )

            if set(created) != set(TRIGGERS):
                raise RuntimeError("No se verificaron todos los triggers esperados.")

        print("Funciones y triggers instalados correctamente.")
        print(f"Base: {TARGET_DATABASE}")
        print(f"Funciones: {len(FUNCTIONS)}")
        print(f"Triggers: {len(TRIGGERS)}")
        print("No se modificaron tablas, políticas RLS ni migraciones.")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
