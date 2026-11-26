"""Guardar por separado el IVA de cada gasto.

Revision ID: d4e8a2f61c37
Revises: b72e91c4a630
Create Date: 2026-11-25

`monto` sigue siendo el total pagado (con IVA); `iva` es la parte de impuesto que
incluye. Los gastos existentes quedan con IVA 0 (no se puede deducir después).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e8a2f61c37"
down_revision: str | Sequence[str] | None = "b72e91c4a630"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "gasto",
        sa.Column("iva", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
    )
    op.create_check_constraint(op.f("gasto_iva_check"), "gasto", "iva >= 0 AND iva <= monto")


def downgrade() -> None:
    op.drop_constraint(op.f("gasto_iva_check"), "gasto", type_="check")
    op.drop_column("gasto", "iva")
