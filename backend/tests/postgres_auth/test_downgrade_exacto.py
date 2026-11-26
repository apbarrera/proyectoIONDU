"""La bajada de e1f3a5b7c902 y d6a8c0e2f417 deja la base EXACTAMENTE como estaba.

Se toma una foto de todo lo que tocan las migraciones (permisos de tabla y de columna con su
otorgante, dueños, RLS, políticas y funciones con su dueño, permisos, configuración y
comentario), se sube a head, se baja y se compara la foto. Los permisos se comparan como
conjuntos (PostgreSQL puede reordenar las entradas del ACL al revocar y volver a conceder).

Única diferencia aceptada: los roles iondu_auth e iondu_funciones siguen existiendo, sin
ningún permiso ni objeto (los roles son globales del clúster; las migraciones no los borran,
igual que b72e91c4a630).
"""

import pytest

from tests.postgres_auth.conftest import PREFIJO, admin, borrar_base, crear_base, migrar

ANTES = "c4e6a8b0d215"

# Un ACL como conjunto ordenado (el orden de sus entradas no importa).
ACL = "(SELECT array_agg(x::text ORDER BY x::text) FROM unnest({}) x)"

FOTO = {
    "tablas": """
        SELECT c.relname, c.relkind, pg_get_userbyid(c.relowner), {acl_tabla},
               c.relrowsecurity, c.relforcerowsecurity
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'S') ORDER BY 1
    """.format(acl_tabla=ACL.format("c.relacl")),
    "columnas": """
        SELECT c.relname, a.attname, {acl_columna}
        FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND a.attnum > 0 AND a.attacl IS NOT NULL ORDER BY 1, 2
    """.format(acl_columna=ACL.format("a.attacl")),
    "politicas": """
        SELECT tablename, policyname, permissive, roles::text, cmd, qual, with_check
        FROM pg_policies ORDER BY 1, 2
    """,
    "funciones": """
        SELECT p.oid::regprocedure::text, pg_get_userbyid(p.proowner), {acl_funcion},
               p.proconfig::text, p.prosecdef, obj_description(p.oid, 'pg_proc')
        FROM pg_proc p WHERE p.pronamespace = 'public'::regnamespace ORDER BY 1
    """.format(acl_funcion=ACL.format("p.proacl")),
    "esquema": f"SELECT {ACL.format('nspacl')} FROM pg_namespace WHERE nspname = 'public'",
}


def _foto(base: str) -> dict:
    with admin(base) as conn:
        return {clave: conn.execute(sql).fetchall() for clave, sql in FOTO.items()}


def _sin_privilegios(base: str, rol: str) -> None:
    with admin(base) as conn:
        assert (
            conn.execute(
                """
            SELECT count(*) FROM pg_class c, aclexplode(c.relacl) p
            WHERE p.grantee = to_regrole(%(r)s)
            """,
                {"r": rol},
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT count(*) FROM pg_attribute a, aclexplode(a.attacl) p "
                "WHERE p.grantee = to_regrole(%(r)s)",
                {"r": rol},
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT count(*) FROM pg_proc WHERE proowner = to_regrole(%(r)s)", {"r": rol}
            ).fetchone()[0]
            == 0
        )


@pytest.mark.parametrize("dueno_funciones", ("administrador", "iondu_migrator"))
def test_la_bajada_restaura_permisos_y_duenos_exactos(cluster, dueno_funciones):
    nombre = f"{PREFIJO}bajada_{dueno_funciones}"
    crear_base(nombre)
    try:
        migrar(nombre, "upgrade", ANTES)
        if dueno_funciones == "iondu_migrator":
            # Como en la base del equipo: funciones de iondu_migrator, con un comentario propio.
            with admin(nombre) as conn:
                conn.execute(
                    "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = "
                    "'iondu_migrator') THEN CREATE ROLE iondu_migrator NOLOGIN NOSUPERUSER "
                    "NOBYPASSRLS; END IF; END $$"
                )
                conn.execute("GRANT ALL ON ALL TABLES IN SCHEMA public TO iondu_migrator")
                conn.execute(
                    "ALTER FUNCTION public.app_es_admin_de(integer) OWNER TO iondu_migrator"
                )
                conn.execute(
                    "ALTER FUNCTION public.app_usuario_en_otras_empresas(uuid, integer) "
                    "OWNER TO iondu_migrator"
                )
                conn.execute(
                    "COMMENT ON FUNCTION public.app_es_admin_de(integer) IS 'Comentario del equipo'"
                )
        antes = _foto(nombre)

        migrar(nombre, "upgrade", "head")
        assert _foto(nombre) != antes  # la subida sí cambia algo
        migrar(nombre, "downgrade", ANTES)

        despues = _foto(nombre)
        for clave in FOTO:
            assert despues[clave] == antes[clave], f"La bajada no restauró: {clave}"
        _sin_privilegios(nombre, "iondu_auth")
        _sin_privilegios(nombre, "iondu_funciones")
    finally:
        borrar_base(nombre)
