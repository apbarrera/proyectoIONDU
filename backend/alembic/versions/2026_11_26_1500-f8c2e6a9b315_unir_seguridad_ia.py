"""Unir las ramas de migraciones de seguridad e IA.

Revision ID: f8c2e6a9b315
Revises: d1f3a5c7e924, d6a8c0e2f417
Create Date: 2026-11-26
"""

from collections.abc import Sequence

revision: str = "f8c2e6a9b315"
down_revision: str | Sequence[str] | None = (
    "d1f3a5c7e924",
    "d6a8c0e2f417",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
