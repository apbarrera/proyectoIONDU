"""Crear la tabla de auditoría (solo inserción).

- La escribe la API después de cada acción importante; el navegador no puede crearla
  ni alterarla.
- iondu_app solo puede INSERTAR (sin UPDATE ni DELETE): el historial no se edita.
- RLS: cualquier usuario de la empresa inserta registros de su empresa a su nombre; solo
  el Administrador los lee. Como un Operativo no puede leerlos, la API inserta sin
  RETURNING (si no, PostgreSQL exigiría también la política de lectura).

Revision ID: b8d2f4a6c913
Revises: a3c5e7f9b104
Create Date: 2026-11-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b8d2f4a6c913"
down_revision: str | Sequence[str] | None = "a3c5e7f9b104"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MODULOS = (
    "auth",
    "ventas",
    "facturacion",
    "gastos",
    "inventario",
    "ia",
    "configuracion",
    "usuarios",
)
EMPRESA_ACTUAL = "NULLIF(current_setting('app.current_empresa_id', true), '')::integer"
USUARIO_ACTUAL = "NULLIF(current_setting('app.current_user_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "auditoria",
        sa.Column("id_auditoria", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("id_empresa", sa.Integer(), nullable=False),
        sa.Column("id_usuario", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "fecha", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("modulo", sa.String(length=20), nullable=False),
        sa.Column("accion", sa.String(length=100), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("entidad", sa.String(length=50), nullable=True),
        sa.Column("id_entidad", sa.String(length=50), nullable=True),
        sa.CheckConstraint(
            "modulo IN (" + ", ".join(f"'{m}'" for m in MODULOS) + ")",
            name=op.f("auditoria_modulo_check"),
        ),
        sa.ForeignKeyConstraint(
            ["id_empresa"],
            ["empresa.id_empresa"],
            name=op.f("auditoria_id_empresa_fkey"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["id_usuario"],
            ["usuario.id"],
            name=op.f("auditoria_id_usuario_fkey"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id_auditoria", name=op.f("auditoria_pkey")),
    )
    op.create_index("idx_auditoria_empresa_fecha", "auditoria", ["id_empresa", "fecha"])

    op.execute("ALTER TABLE public.auditoria ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.auditoria FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY auditoria_app_admin_select ON public.auditoria
        FOR SELECT TO iondu_app
        USING (id_empresa = {EMPRESA_ACTUAL} AND public.app_es_admin_de(id_empresa))
        """
    )
    op.execute(
        f"""
        CREATE POLICY auditoria_app_insert ON public.auditoria
        FOR INSERT TO iondu_app
        WITH CHECK (
            id_empresa = {EMPRESA_ACTUAL}
            AND (id_usuario IS NULL OR id_usuario = {USUARIO_ACTUAL})
        )
        """
    )
    op.execute("GRANT SELECT ON public.auditoria TO iondu_app")
    op.execute(
        "GRANT INSERT (id_empresa, id_usuario, modulo, accion, descripcion, entidad, id_entidad) "
        "ON public.auditoria TO iondu_app"
    )


def downgrade() -> None:
    op.drop_index("idx_auditoria_empresa_fecha", table_name="auditoria")
    op.drop_table("auditoria")
