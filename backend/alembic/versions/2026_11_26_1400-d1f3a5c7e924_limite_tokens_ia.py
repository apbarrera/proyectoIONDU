"""Límite mensual de tokens del agente de IA por empresa (RF-6.1, RF-6.14, RNF-12).

El Administrador lo configura; NULL significa sin límite. iondu_app solo puede
actualizar esta columna, además de las que ya tenía.

Revision ID: d1f3a5c7e924
Revises: c4e6a8b0d215
Create Date: 2026-11-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d1f3a5c7e924"
down_revision: str | Sequence[str] | None = "c4e6a8b0d215"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("empresa", sa.Column("limite_tokens_ia_mensual", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "empresa_limite_tokens_ia_check",
        "empresa",
        "limite_tokens_ia_mensual IS NULL OR limite_tokens_ia_mensual >= 0",
    )
    op.execute("GRANT UPDATE (limite_tokens_ia_mensual) ON public.empresa TO iondu_app")


def downgrade() -> None:
    op.execute("REVOKE UPDATE (limite_tokens_ia_mensual) ON public.empresa FROM iondu_app")
    op.drop_constraint("empresa_limite_tokens_ia_check", "empresa", type_="check")
    op.drop_column("empresa", "limite_tokens_ia_mensual")
