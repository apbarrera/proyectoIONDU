"""Habilitar RLS multitenant para API y worker.

Revision ID: a91d6e4c2b70
Revises: f3a8c1d72e90
Create Date: 2026-11-21
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a91d6e4c2b70"
down_revision: str | Sequence[str] | None = "f3a8c1d72e90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TABLAS_TENANT = (
    "categoria_gasto",
    "categoria_producto",
    "cliente",
    "proveedor",
    "producto",
    "venta",
    "detalle_venta",
    "movimiento_inventario",
    "gasto",
    "factura",
    "secuencia_comprobante",
    "accion_ia",
    "consumo_tokens",
    "recomendacion",
)

TABLAS_RLS = (
    "empresa",
    "usuario_empresa",
    "rol",
    "dashboard_financiero",
    *TABLAS_TENANT,
)


def upgrade() -> None:
    # Todas las tablas quedan protegidas incluso cuando la conexión
    # pertenece al propietario de la tabla (salvo superusuario/BYPASSRLS).
    for tabla in TABLAS_RLS:
        op.execute(f'ALTER TABLE public."{tabla}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE public."{tabla}" FORCE ROW LEVEL SECURITY')

    # El usuario autenticado solo puede consultar sus propias membresías.
    op.execute(
        """
        CREATE POLICY usuario_empresa_app_select
        ON public.usuario_empresa
        FOR SELECT
        USING (
            current_user = 'iondu_app'
            AND id_usuario =
                NULLIF(current_setting('app.current_user_id', true), '')::uuid
        )
        """
    )

    # Los roles son un catálogo global de lectura para la API.
    op.execute(
        """
        CREATE POLICY rol_app_select
        ON public.rol
        FOR SELECT
        USING (current_user = 'iondu_app')
        """
    )

    # La API puede consultar empresas donde el usuario tenga membresía activa.
    # No se exige empresa seleccionada: este acceso permite cargar membresías.
    op.execute(
        """
        CREATE POLICY empresa_app_select
        ON public.empresa
        FOR SELECT
        USING (
            current_user = 'iondu_app'
            AND EXISTS (
                SELECT 1
                FROM public.usuario_empresa AS ue
                WHERE ue.id_usuario =
                    NULLIF(current_setting('app.current_user_id', true), '')::uuid
                  AND ue.id_empresa = empresa.id_empresa
                  AND ue.estado = 'ACTIVO'
            )
        )
        """
    )

    # Solo administradores de la empresa seleccionada pueden modificar
    # la configuración de certificados. Los GRANT por columna se gestionan
    # separadamente y siguen siendo obligatorios.
    op.execute(
        """
        CREATE POLICY empresa_app_update
        ON public.empresa
        FOR UPDATE
        USING (
            current_user = 'iondu_app'
            AND id_empresa =
                NULLIF(current_setting('app.current_empresa_id', true), '')::integer
            AND EXISTS (
                SELECT 1
                FROM public.usuario_empresa AS ue
                JOIN public.rol AS r ON r.id_rol = ue.id_rol
                WHERE ue.id_usuario =
                    NULLIF(current_setting('app.current_user_id', true), '')::uuid
                  AND ue.id_empresa = empresa.id_empresa
                  AND ue.estado = 'ACTIVO'
                  AND r.nombre = 'Administrador'
            )
        )
        WITH CHECK (
            current_user = 'iondu_app'
            AND id_empresa =
                NULLIF(current_setting('app.current_empresa_id', true), '')::integer
            AND EXISTS (
                SELECT 1
                FROM public.usuario_empresa AS ue
                JOIN public.rol AS r ON r.id_rol = ue.id_rol
                WHERE ue.id_usuario =
                    NULLIF(current_setting('app.current_user_id', true), '')::uuid
                  AND ue.id_empresa = empresa.id_empresa
                  AND ue.estado = 'ACTIVO'
                  AND r.nombre = 'Administrador'
            )
        )
        """
    )

    # Aislamiento por empresa para las tablas de negocio.
    # La membresía se vuelve a comprobar dentro de PostgreSQL.
    for tabla in TABLAS_TENANT:
        op.execute(
            f"""
            CREATE POLICY {tabla}_app_tenant
            ON public."{tabla}"
            FOR ALL
            USING (
                current_user = 'iondu_app'
                AND id_empresa =
                    NULLIF(current_setting('app.current_empresa_id', true), '')::integer
                AND EXISTS (
                    SELECT 1
                    FROM public.usuario_empresa AS ue
                    WHERE ue.id_usuario =
                        NULLIF(current_setting('app.current_user_id', true), '')::uuid
                      AND ue.id_empresa =
                        NULLIF(current_setting('app.current_empresa_id', true), '')::integer
                      AND ue.estado = 'ACTIVO'
                )
            )
            WITH CHECK (
                current_user = 'iondu_app'
                AND id_empresa =
                    NULLIF(current_setting('app.current_empresa_id', true), '')::integer
                AND EXISTS (
                    SELECT 1
                    FROM public.usuario_empresa AS ue
                    WHERE ue.id_usuario =
                        NULLIF(current_setting('app.current_user_id', true), '')::uuid
                      AND ue.id_empresa =
                        NULLIF(current_setting('app.current_empresa_id', true), '')::integer
                      AND ue.estado = 'ACTIVO'
                )
            )
            """
        )

    # El dashboard requiere membresía activa y rol Administrador.
    op.execute(
        """
        CREATE POLICY dashboard_financiero_app_admin
        ON public.dashboard_financiero
        FOR ALL
        USING (
            current_user = 'iondu_app'
            AND id_empresa =
                NULLIF(current_setting('app.current_empresa_id', true), '')::integer
            AND EXISTS (
                SELECT 1
                FROM public.usuario_empresa AS ue
                JOIN public.rol AS r ON r.id_rol = ue.id_rol
                WHERE ue.id_usuario =
                    NULLIF(current_setting('app.current_user_id', true), '')::uuid
                  AND ue.id_empresa = dashboard_financiero.id_empresa
                  AND ue.estado = 'ACTIVO'
                  AND r.nombre = 'Administrador'
            )
        )
        WITH CHECK (
            current_user = 'iondu_app'
            AND id_empresa =
                NULLIF(current_setting('app.current_empresa_id', true), '')::integer
            AND EXISTS (
                SELECT 1
                FROM public.usuario_empresa AS ue
                JOIN public.rol AS r ON r.id_rol = ue.id_rol
                WHERE ue.id_usuario =
                    NULLIF(current_setting('app.current_user_id', true), '')::uuid
                  AND ue.id_empresa = dashboard_financiero.id_empresa
                  AND ue.estado = 'ACTIVO'
                  AND r.nombre = 'Administrador'
            )
        )
        """
    )

    # El worker consulta facturas de todas las empresas, pero solo aquellas
    # pendientes o autorizadas (estas últimas para registrar el RIDE).
    op.execute(
        """
        CREATE POLICY factura_worker_select
        ON public.factura
        FOR SELECT
        USING (
            current_user = 'iondu_worker'
            AND estado_autorizacion IN (
                'por_enviar',
                'por_autorizar',
                'autorizada'
            )
        )
        """
    )

    # El worker puede procesar facturas pendientes y registrar el RIDE
    # de facturas autorizadas. Los GRANT por columna limitan qué modifica.
    op.execute(
        """
        CREATE POLICY factura_worker_update
        ON public.factura
        FOR UPDATE
        USING (
            current_user = 'iondu_worker'
            AND estado_autorizacion IN (
                'por_enviar',
                'por_autorizar',
                'autorizada'
            )
        )
        WITH CHECK (
            current_user = 'iondu_worker'
            AND estado_autorizacion IN (
                'autorizada',
                'rechazada',
                'por_enviar',
                'por_autorizar'
            )
        )
        """
    )

    # El worker solo puede consultar la empresa asociada a facturas
    # que están en estados que su proceso necesita atender.
    op.execute(
        """
        CREATE POLICY empresa_worker_select
        ON public.empresa
        FOR SELECT
        USING (
            current_user = 'iondu_worker'
            AND EXISTS (
                SELECT 1
                FROM public.factura AS f
                WHERE f.id_empresa = empresa.id_empresa
                  AND f.estado_autorizacion IN (
                      'por_enviar',
                      'por_autorizar',
                      'autorizada'
                  )
            )
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS empresa_worker_select ON public.empresa")
    op.execute("DROP POLICY IF EXISTS factura_worker_update ON public.factura")
    op.execute("DROP POLICY IF EXISTS factura_worker_select ON public.factura")
    op.execute(
        "DROP POLICY IF EXISTS dashboard_financiero_app_admin ON public.dashboard_financiero"
    )

    for tabla in reversed(TABLAS_TENANT):
        op.execute(f'DROP POLICY IF EXISTS {tabla}_app_tenant ON public."{tabla}"')

    op.execute("DROP POLICY IF EXISTS empresa_app_update ON public.empresa")
    op.execute("DROP POLICY IF EXISTS empresa_app_select ON public.empresa")
    op.execute("DROP POLICY IF EXISTS rol_app_select ON public.rol")
    op.execute("DROP POLICY IF EXISTS usuario_empresa_app_select ON public.usuario_empresa")

    for tabla in reversed(TABLAS_RLS):
        op.execute(f'ALTER TABLE public."{tabla}" NO FORCE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE public."{tabla}" DISABLE ROW LEVEL SECURITY')
