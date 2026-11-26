"""Enlaces de un solo uso para recuperar la contraseña o aceptar una invitación.

Como `sesion_refresh`, la tabla no usa RLS por empresa: la API busca al usuario por
correo antes de saber quién es. iondu_app solo inserta, lee y marca el enlace como usado;
el worker no recibe permisos.

Revision ID: e7a9c1d3f526
Revises: d1f3a5c7e924
Create Date: 2026-11-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e7a9c1d3f526"
down_revision: str | Sequence[str] | None = "d1f3a5c7e924"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "restablecimiento_contrasena",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("id_usuario", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("motivo", sa.String(length=20), nullable=False),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usado_en", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "motivo IN ('recuperacion', 'invitacion')", name="restablecimiento_motivo_check"
        ),
        sa.ForeignKeyConstraint(
            ["id_usuario"],
            ["usuario.id"],
            name=op.f("restablecimiento_contrasena_id_usuario_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("restablecimiento_contrasena_pkey")),
        sa.UniqueConstraint("token_hash", name=op.f("restablecimiento_contrasena_token_hash_key")),
    )
    op.create_index("idx_restablecimiento_usuario", "restablecimiento_contrasena", ["id_usuario"])
    op.execute("GRANT SELECT, INSERT ON public.restablecimiento_contrasena TO iondu_auth")
    op.execute("GRANT UPDATE (usado_en) ON public.restablecimiento_contrasena TO iondu_auth")


def downgrade() -> None:
    op.drop_index("idx_restablecimiento_usuario", table_name="restablecimiento_contrasena")
    op.drop_table("restablecimiento_contrasena")
