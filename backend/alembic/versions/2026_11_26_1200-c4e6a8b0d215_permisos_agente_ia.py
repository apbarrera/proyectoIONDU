"""Permisos de iondu_app para el agente de IA.

accion_ia y consumo_tokens existían sin funcionalidad y sin permisos. El agente:
- inserta cada interacción en accion_ia y cambia solo su estado y su payload al
  confirmarla o cancelarla (nunca la borra: es el historial, RF-6.13);
- inserta el consumo de tokens de cada llamada al modelo (RF-6.14).
Ambas tablas ya tienen RLS por empresa (migración a91d6e4c2b70).

Revision ID: c4e6a8b0d215
Revises: b8d2f4a6c913
Create Date: 2026-11-26
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c4e6a8b0d215"
down_revision: str | Sequence[str] | None = "b8d2f4a6c913"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("GRANT SELECT, INSERT ON public.accion_ia TO iondu_app")
    op.execute("GRANT UPDATE (estado, payload_json) ON public.accion_ia TO iondu_app")
    op.execute("GRANT SELECT, INSERT ON public.consumo_tokens TO iondu_app")


def downgrade() -> None:
    op.execute("REVOKE SELECT, INSERT ON public.consumo_tokens FROM iondu_app")
    op.execute("REVOKE UPDATE (estado, payload_json) ON public.accion_ia FROM iondu_app")
    op.execute("REVOKE SELECT, INSERT ON public.accion_ia FROM iondu_app")
