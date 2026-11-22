"""Restringir eliminaciones de empresas y ventas con datos relacionados.

Revision ID: c82f6a91d304
Revises: b71c9d4e2a10
Create Date: 2026-11-17
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c82f6a91d304"
down_revision: str | Sequence[str] | None = "b71c9d4e2a10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Restricciones directas de las tablas de negocio hacia empresa.
FK_EMPRESA = (
    ("accion_ia_id_empresa_fkey", "accion_ia", ["id_empresa"], ["id_empresa"]),
    ("categoria_gasto_id_empresa_fkey", "categoria_gasto", ["id_empresa"], ["id_empresa"]),
    ("categoria_producto_id_empresa_fkey", "categoria_producto", ["id_empresa"], ["id_empresa"]),
    ("cliente_id_empresa_fkey", "cliente", ["id_empresa"], ["id_empresa"]),
    ("consumo_tokens_id_empresa_fkey", "consumo_tokens", ["id_empresa"], ["id_empresa"]),
    (
        "dashboard_financiero_id_empresa_fkey",
        "dashboard_financiero",
        ["id_empresa"],
        ["id_empresa"],
    ),
    ("factura_id_empresa_fkey", "factura", ["id_empresa"], ["id_empresa"]),
    ("gasto_id_empresa_fkey", "gasto", ["id_empresa"], ["id_empresa"]),
    ("producto_id_empresa_fkey", "producto", ["id_empresa"], ["id_empresa"]),
    ("proveedor_id_empresa_fkey", "proveedor", ["id_empresa"], ["id_empresa"]),
    ("recomendacion_id_empresa_fkey", "recomendacion", ["id_empresa"], ["id_empresa"]),
    (
        "secuencia_comprobante_id_empresa_fkey",
        "secuencia_comprobante",
        ["id_empresa"],
        ["id_empresa"],
    ),
    ("usuario_empresa_id_empresa_fkey", "usuario_empresa", ["id_empresa"], ["id_empresa"]),
    ("venta_id_empresa_fkey", "venta", ["id_empresa"], ["id_empresa"]),
)

# Restricciones compuestas de los registros dependientes hacia venta.
FK_VENTA = (
    (
        "detalle_venta_empresa_venta_fk",
        "detalle_venta",
        ["id_empresa", "id_venta"],
        ["id_empresa", "id_venta"],
    ),
    (
        "factura_venta_empresa_fk",
        "factura",
        ["id_empresa", "id_venta"],
        ["id_empresa", "id_venta"],
    ),
)


def _cambiar_ondelete(restricciones, accion: str) -> None:
    for nombre, tabla, columnas_locales, columnas_remotas in restricciones:
        op.drop_constraint(
            nombre,
            tabla,
            type_="foreignkey",
        )
        op.create_foreign_key(
            nombre,
            tabla,
            "empresa" if nombre.endswith("_id_empresa_fkey") else "venta",
            columnas_locales,
            columnas_remotas,
            ondelete=accion,
        )


def upgrade() -> None:
    _cambiar_ondelete(FK_EMPRESA, "RESTRICT")
    _cambiar_ondelete(FK_VENTA, "RESTRICT")


def downgrade() -> None:
    _cambiar_ondelete(tuple(reversed(FK_VENTA)), "CASCADE")
    _cambiar_ondelete(tuple(reversed(FK_EMPRESA)), "CASCADE")
