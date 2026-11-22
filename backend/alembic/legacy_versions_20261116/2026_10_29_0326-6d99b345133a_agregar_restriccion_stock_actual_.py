"""Agregar restricción de stock actual de producto.

Revision ID: 6d99b345133a
Revises: ae0ae8ee9f73
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "6d99b345133a"
down_revision: str | Sequence[str] | None = "ae0ae8ee9f73"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        op.f("producto_stock_actual_check"),
        "producto",
        "stock_actual >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("producto_stock_actual_check"),
        "producto",
        type_="check",
    )
