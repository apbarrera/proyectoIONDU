"""unir seguridad ia y correo

Revision ID: fd09a182da8d
Revises: f8c2e6a9b315, f9b1d3e5a738
Create Date: 2026-11-26 15:29:35.394216-05:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Identificadores de la migración, usados por Alembic.
revision: str = "fd09a182da8d"
down_revision: str | Sequence[str] | None = ("f8c2e6a9b315", "f9b1d3e5a738")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
