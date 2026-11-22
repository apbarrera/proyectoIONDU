"""agregar empresa a movimientos de inventario

Revision ID: ae0ae8ee9f73
Revises: 04cc3aeec02f
Create Date: 2026-10-28 00:31:24.989438-05:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Identificadores de la migración, usados por Alembic.
revision: str = "ae0ae8ee9f73"
down_revision: str | Sequence[str] | None = "04cc3aeec02f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "movimiento_inventario",
        sa.Column("id_empresa", sa.Integer(), nullable=False),
    )

    op.create_index(
        "idx_movimiento_empresa",
        "movimiento_inventario",
        ["id_empresa"],
        unique=False,
    )

    op.drop_constraint(
        "movimiento_inventario_id_usuario_fkey",
        "movimiento_inventario",
        type_="foreignkey",
    )

    op.drop_constraint(
        "movimiento_inventario_id_producto_fkey",
        "movimiento_inventario",
        type_="foreignkey",
    )

    op.create_foreign_key(
        "movimiento_inventario_usuario_empresa_fkey",
        "movimiento_inventario",
        "usuario_empresa",
        ["id_usuario", "id_empresa"],
        ["id_usuario", "id_empresa"],
        ondelete="RESTRICT",
    )

    op.create_foreign_key(
        "movimiento_inventario_empresa_producto_fkey",
        "movimiento_inventario",
        "producto",
        ["id_empresa", "id_producto"],
        ["id_empresa", "id_producto"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "movimiento_inventario_empresa_producto_fkey",
        "movimiento_inventario",
        type_="foreignkey",
    )

    op.drop_constraint(
        "movimiento_inventario_usuario_empresa_fkey",
        "movimiento_inventario",
        type_="foreignkey",
    )

    op.create_foreign_key(
        "movimiento_inventario_id_producto_fkey",
        "movimiento_inventario",
        "producto",
        ["id_producto"],
        ["id_producto"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "movimiento_inventario_id_usuario_fkey",
        "movimiento_inventario",
        "users",
        ["id_usuario"],
        ["id"],
        referent_schema="auth",
        ondelete="RESTRICT",
    )

    op.drop_index(
        "idx_movimiento_empresa",
        table_name="movimiento_inventario",
    )

    op.drop_column(
        "movimiento_inventario",
        "id_empresa",
    )
