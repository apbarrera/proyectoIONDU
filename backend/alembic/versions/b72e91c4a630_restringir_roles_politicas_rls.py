"""Restringir las políticas RLS a sus roles correspondientes.

Revision ID: b72e91c4a630
Revises: a91d6e4c2b70
"""

from alembic import op

revision: str = "b72e91c4a630"
down_revision: str | None = "a91d6e4c2b70"
branch_labels: str | None = None
depends_on: str | None = None


POLITICAS = (
    ("accion_ia", "accion_ia_app_tenant", "iondu_app"),
    ("categoria_gasto", "categoria_gasto_app_tenant", "iondu_app"),
    ("categoria_producto", "categoria_producto_app_tenant", "iondu_app"),
    ("cliente", "cliente_app_tenant", "iondu_app"),
    ("consumo_tokens", "consumo_tokens_app_tenant", "iondu_app"),
    ("dashboard_financiero", "dashboard_financiero_app_admin", "iondu_app"),
    ("detalle_venta", "detalle_venta_app_tenant", "iondu_app"),
    ("empresa", "empresa_app_select", "iondu_app"),
    ("empresa", "empresa_app_update", "iondu_app"),
    ("factura", "factura_app_tenant", "iondu_app"),
    ("gasto", "gasto_app_tenant", "iondu_app"),
    ("movimiento_inventario", "movimiento_inventario_app_tenant", "iondu_app"),
    ("producto", "producto_app_tenant", "iondu_app"),
    ("proveedor", "proveedor_app_tenant", "iondu_app"),
    ("recomendacion", "recomendacion_app_tenant", "iondu_app"),
    ("rol", "rol_app_select", "iondu_app"),
    ("secuencia_comprobante", "secuencia_comprobante_app_tenant", "iondu_app"),
    ("usuario_empresa", "usuario_empresa_app_select", "iondu_app"),
    ("venta", "venta_app_tenant", "iondu_app"),
    ("empresa", "empresa_worker_select", "iondu_worker"),
    ("factura", "factura_worker_select", "iondu_worker"),
    ("factura", "factura_worker_update", "iondu_worker"),
)


def upgrade() -> None:
    # Una base nueva (local, CI o de evaluación) no tiene estos roles y ALTER POLICY
    # fallaría. Se crean NOLOGIN: nadie puede conectarse con ellos hasta que el
    # despliegue les asigne LOGIN y contraseña. Si ya existen, no se tocan.
    for rol in sorted({rol for _tabla, _politica, rol in POLITICAS}):
        op.execute(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{rol}') THEN
                    CREATE ROLE "{rol}" NOLOGIN NOSUPERUSER NOBYPASSRLS;
                END IF;
            END
            $$;
            """
        )

    for tabla, politica, rol in POLITICAS:
        op.execute(f'ALTER POLICY "{politica}" ON public."{tabla}" TO "{rol}"')


def downgrade() -> None:
    for tabla, politica, _rol in reversed(POLITICAS):
        op.execute(f'ALTER POLICY "{politica}" ON public."{tabla}" TO PUBLIC')
