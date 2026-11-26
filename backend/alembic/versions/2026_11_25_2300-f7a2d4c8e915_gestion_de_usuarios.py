"""Permitir que el Administrador gestione los usuarios de su empresa.

Hasta ahora cada usuario solo veía sus propias pertenencias. El Administrador de la
empresa seleccionada necesita ver, agregar y modificar las de su empresa.

Una política sobre usuario_empresa no puede consultar usuario_empresa (PostgreSQL
detecta recursión infinita), así que la comprobación "¿es Administrador de esta
empresa?" vive en una función SECURITY DEFINER. Lo mismo para saber si un usuario
pertenece a OTRAS empresas, que el Administrador no puede ver: con eso se impide
que el Administrador de una empresa restablezca la contraseña de alguien que
también trabaja en otra.

Revision ID: f7a2d4c8e915
Revises: e5b1c7a9d203
Create Date: 2026-11-25
"""

from collections.abc import Sequence

from alembic import op

revision: str = "f7a2d4c8e915"
down_revision: str | Sequence[str] | None = "e5b1c7a9d203"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMPRESA_ACTUAL = "NULLIF(current_setting('app.current_empresa_id', true), '')::integer"
CONDICION_ADMIN = f"id_empresa = {EMPRESA_ACTUAL} AND public.app_es_admin_de(id_empresa)"


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.app_es_admin_de(p_empresa integer)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
            SELECT EXISTS (
                SELECT 1
                FROM public.usuario_empresa AS ue
                JOIN public.rol AS r ON r.id_rol = ue.id_rol
                WHERE ue.id_usuario =
                        NULLIF(current_setting('app.current_user_id', true), '')::uuid
                  AND ue.id_empresa = p_empresa
                  AND ue.estado = 'ACTIVO'
                  AND r.nombre = 'Administrador'
            );
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.app_usuario_en_otras_empresas(
            p_usuario uuid, p_empresa integer
        )
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
            SELECT EXISTS (
                SELECT 1
                FROM public.usuario_empresa AS ue
                WHERE ue.id_usuario = p_usuario
                  AND ue.id_empresa <> p_empresa
                  AND ue.estado = 'ACTIVO'
            );
        $$;
        """
    )
    for funcion in (
        "public.app_es_admin_de(integer)",
        "public.app_usuario_en_otras_empresas(uuid, integer)",
    ):
        op.execute(f"REVOKE ALL ON FUNCTION {funcion} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {funcion} TO iondu_app")

    op.execute(
        f"""
        CREATE POLICY usuario_empresa_app_admin_select ON public.usuario_empresa
        FOR SELECT TO iondu_app USING ({CONDICION_ADMIN})
        """
    )
    op.execute(
        f"""
        CREATE POLICY usuario_empresa_app_admin_insert ON public.usuario_empresa
        FOR INSERT TO iondu_app WITH CHECK ({CONDICION_ADMIN})
        """
    )
    op.execute(
        f"""
        CREATE POLICY usuario_empresa_app_admin_update ON public.usuario_empresa
        FOR UPDATE TO iondu_app USING ({CONDICION_ADMIN}) WITH CHECK ({CONDICION_ADMIN})
        """
    )

    op.execute("GRANT SELECT, INSERT ON public.usuario_empresa TO iondu_app")
    op.execute(
        "GRANT UPDATE (id_rol, estado, nombre_visible) ON public.usuario_empresa TO iondu_app"
    )
    # Crear cuentas nuevas desde la gestión de usuarios (correo y hash, nada más).
    op.execute("GRANT INSERT (id, email, password_hash) ON public.usuario TO iondu_app")


def downgrade() -> None:
    op.execute("REVOKE INSERT (id, email, password_hash) ON public.usuario FROM iondu_app")
    op.execute(
        "REVOKE UPDATE (id_rol, estado, nombre_visible) ON public.usuario_empresa FROM iondu_app"
    )
    op.execute("REVOKE INSERT ON public.usuario_empresa FROM iondu_app")
    for politica in ("select", "insert", "update"):
        op.execute(
            f"DROP POLICY IF EXISTS usuario_empresa_app_admin_{politica} ON public.usuario_empresa"
        )
    op.execute("DROP FUNCTION IF EXISTS public.app_usuario_en_otras_empresas(uuid, integer)")
    op.execute("DROP FUNCTION IF EXISTS public.app_es_admin_de(integer)")
