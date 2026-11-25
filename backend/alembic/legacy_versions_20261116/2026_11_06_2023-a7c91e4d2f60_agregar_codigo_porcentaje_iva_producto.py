"""Agregar código de porcentaje IVA al producto.

Revision ID: a7c91e4d2f60
Revises: 6d99b345133a
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7c91e4d2f60"
down_revision: str | Sequence[str] | None = "6d99b345133a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Agregar temporalmente la columna como nullable.
    op.add_column(
        "producto",
        sa.Column(
            "codigo_porcentaje_iva",
            sa.String(length=2),
            nullable=True,
        ),
    )

    # Conservar el tratamiento tributario de los productos existentes.
    op.execute(
        """
        UPDATE producto
        SET codigo_porcentaje_iva =
            CASE
                WHEN aplica_iva IS TRUE THEN '4'
                ELSE '0'
            END
        """
    )

    # Establecer obligatoriedad y valor predeterminado.
    op.alter_column(
        "producto",
        "codigo_porcentaje_iva",
        existing_type=sa.String(length=2),
        nullable=False,
        server_default=sa.text("'4'"),
    )

    # Limitar los códigos admitidos.
    op.create_check_constraint(
        op.f("producto_codigo_porcentaje_iva_check"),
        "producto",
        "codigo_porcentaje_iva IN ('0', '4', '5', '6', '7')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "producto_codigo_porcentaje_iva_check",
        "producto",
        type_="check",
    )

    op.drop_column("producto", "codigo_porcentaje_iva")
