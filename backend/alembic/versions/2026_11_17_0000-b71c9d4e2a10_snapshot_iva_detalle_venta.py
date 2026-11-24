"""Guardar el porcentaje y valor histórico de IVA por detalle de venta.

Revision ID: b71c9d4e2a10
Revises: ee649f8f7489
Create Date: 2026-11-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b71c9d4e2a10"
down_revision: str | Sequence[str] | None = "ee649f8f7489"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # No inferir tarifas historicas a partir del codigo SRI.
    # Esta migracion solo puede completar el snapshot en una instalacion
    # limpia, antes de que existan lineas de venta.
    bind = op.get_bind()
    bind.execute(sa.text("LOCK TABLE detalle_venta IN ACCESS EXCLUSIVE MODE"))
    existen_detalles = bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM detalle_venta)")).scalar()

    if existen_detalles:
        raise RuntimeError(
            "No se puede completar el snapshot de IVA: "
            "detalle_venta contiene registros historicos. "
            "Se requiere una reconstruccion auditada de las tarifas "
            "antes de aplicar esta migracion."
        )

    op.add_column(
        "detalle_venta",
        sa.Column("porcentaje_iva", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "detalle_venta",
        sa.Column("valor_iva", sa.Numeric(12, 2), nullable=True),
    )

    op.execute(
        """
        UPDATE detalle_venta
        SET porcentaje_iva = CASE codigo_porcentaje_iva
            WHEN '4' THEN 15.00
            WHEN '5' THEN 5.00
            WHEN '0' THEN 0.00
            WHEN '6' THEN 0.00
            WHEN '7' THEN 0.00
        END
        """
    )

    op.execute(
        """
        UPDATE detalle_venta
        SET valor_iva = ROUND(subtotal * porcentaje_iva / 100, 2)
        """
    )

    op.alter_column(
        "detalle_venta",
        "porcentaje_iva",
        existing_type=sa.Numeric(5, 2),
        nullable=False,
    )
    op.alter_column(
        "detalle_venta",
        "valor_iva",
        existing_type=sa.Numeric(12, 2),
        nullable=False,
    )

    op.create_check_constraint(
        "detalle_venta_porcentaje_iva_rango_ck",
        "detalle_venta",
        "porcentaje_iva >= 0 AND porcentaje_iva <= 100",
    )
    op.create_check_constraint(
        "detalle_venta_valor_iva_check",
        "detalle_venta",
        "valor_iva >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "detalle_venta_valor_iva_check",
        "detalle_venta",
        type_="check",
    )
    op.drop_constraint(
        "detalle_venta_porcentaje_iva_rango_ck",
        "detalle_venta",
        type_="check",
    )
    op.drop_column("detalle_venta", "valor_iva")
    op.drop_column("detalle_venta", "porcentaje_iva")
