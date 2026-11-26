"""Lectura de facturas de proveedores por correo (RF-3.2 y RF-3.3).

- buzon_correo: la cuenta IMAP de cada empresa. La clave va cifrada (como el .p12) y
  solo el worker la descifra en memoria al leer.
- borrador_gasto: lo que el worker encuentra en el correo. El usuario lo confirma
  (se crea el gasto) o lo descarta. Un mismo correo o una misma clave de acceso no
  generan dos borradores (idempotencia, RF-3.2).

RLS: la API (iondu_app) ve y cambia solo lo de la empresa de la sesión; el worker lee
los buzones activos, actualiza su estado de lectura e inserta borradores.

Revision ID: f9b1d3e5a738
Revises: e7a9c1d3f526
Create Date: 2026-11-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f9b1d3e5a738"
down_revision: str | Sequence[str] | None = "e7a9c1d3f526"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMPRESA_SESION = "NULLIF(current_setting('app.current_empresa_id', true), '')::integer"
USUARIO_SESION = "NULLIF(current_setting('app.current_user_id', true), '')::uuid"
MIEMBRO_ACTIVO = (
    "EXISTS (SELECT 1 FROM public.usuario_empresa AS ue "
    f"WHERE ue.id_usuario = {USUARIO_SESION} "
    f"AND ue.id_empresa = {EMPRESA_SESION} AND ue.estado = 'ACTIVO')"
)


def _politica_app(tabla: str) -> None:
    condicion = f"current_user = 'iondu_app' AND id_empresa = {EMPRESA_SESION} AND {MIEMBRO_ACTIVO}"
    op.execute(
        f"CREATE POLICY {tabla}_app_tenant ON public.{tabla} FOR ALL TO iondu_app "
        f"USING ({condicion}) WITH CHECK ({condicion})"
    )


def upgrade() -> None:
    op.create_table(
        "buzon_correo",
        sa.Column("id_empresa", sa.Integer(), nullable=False),
        sa.Column("servidor", sa.String(length=255), nullable=False),
        sa.Column("puerto", sa.Integer(), nullable=False),
        sa.Column("seguridad", sa.String(length=10), nullable=False, server_default="ssl"),
        sa.Column("usuario", sa.String(length=254), nullable=False),
        sa.Column("clave_cifrada", sa.Text(), nullable=False),
        sa.Column("carpeta", sa.String(length=100), nullable=False, server_default="INBOX"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("uid_validity", sa.BigInteger(), nullable=True),
        sa.Column("ultimo_uid", sa.BigInteger(), nullable=True),
        sa.Column("ultima_lectura", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ultimo_error", sa.String(length=300), nullable=True),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("puerto BETWEEN 1 AND 65535", name="buzon_correo_puerto_check"),
        sa.CheckConstraint(
            "seguridad IN ('ssl', 'starttls', 'ninguna')", name="buzon_correo_seguridad_check"
        ),
        sa.ForeignKeyConstraint(
            ["id_empresa"],
            ["empresa.id_empresa"],
            name=op.f("buzon_correo_id_empresa_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id_empresa", name=op.f("buzon_correo_pkey")),
    )

    op.create_table(
        "borrador_gasto",
        sa.Column("id_borrador", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("id_empresa", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.String(length=998), nullable=False),
        sa.Column("clave_acceso", sa.String(length=49), nullable=True),
        sa.Column("remitente", sa.String(length=254), nullable=True),
        sa.Column("asunto", sa.String(length=300), nullable=True),
        sa.Column("recibido_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proveedor_ruc", sa.String(length=13), nullable=True),
        sa.Column("proveedor_nombre", sa.String(length=300), nullable=True),
        sa.Column("numero_comprobante", sa.String(length=20), nullable=True),
        sa.Column("fecha_emision", sa.Date(), nullable=True),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=True),
        sa.Column("iva", sa.Numeric(12, 2), nullable=True),
        sa.Column("total", sa.Numeric(12, 2), nullable=True),
        sa.Column("detalle", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("estado", sa.String(length=15), nullable=False, server_default="PENDIENTE"),
        sa.Column("id_gasto", sa.Integer(), nullable=True),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint(
            "estado IN ('PENDIENTE', 'CONVERTIDO', 'DESCARTADO')",
            name="borrador_gasto_estado_check",
        ),
        sa.ForeignKeyConstraint(
            ["id_empresa"],
            ["empresa.id_empresa"],
            name=op.f("borrador_gasto_id_empresa_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["id_gasto"],
            ["gasto.id_gasto"],
            name=op.f("borrador_gasto_id_gasto_fkey"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id_borrador", name=op.f("borrador_gasto_pkey")),
        sa.UniqueConstraint("id_empresa", "message_id", name="borrador_gasto_empresa_message_uq"),
        sa.UniqueConstraint("id_empresa", "clave_acceso", name="borrador_gasto_empresa_clave_uq"),
    )
    op.create_index("idx_borrador_gasto_empresa_estado", "borrador_gasto", ["id_empresa", "estado"])

    for tabla in ("buzon_correo", "borrador_gasto"):
        op.execute(f"ALTER TABLE public.{tabla} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{tabla} FORCE ROW LEVEL SECURITY")
        _politica_app(tabla)

    # Worker: lee los buzones activos de todas las empresas, guarda hasta dónde leyó e
    # inserta borradores. No ve gastos ni borradores existentes.
    op.execute(
        "CREATE POLICY buzon_correo_worker_select ON public.buzon_correo FOR SELECT "
        "TO iondu_worker USING (current_user = 'iondu_worker' AND activo)"
    )
    op.execute(
        "CREATE POLICY buzon_correo_worker_update ON public.buzon_correo FOR UPDATE "
        "TO iondu_worker USING (current_user = 'iondu_worker' AND activo) "
        "WITH CHECK (current_user = 'iondu_worker')"
    )
    op.execute(
        "CREATE POLICY borrador_gasto_worker_insert ON public.borrador_gasto FOR INSERT "
        "TO iondu_worker WITH CHECK "
        "(current_user = 'iondu_worker' AND estado = 'PENDIENTE' AND id_gasto IS NULL)"
    )

    op.execute("GRANT SELECT, INSERT, DELETE ON public.buzon_correo TO iondu_app")
    op.execute(
        "GRANT UPDATE (servidor, puerto, seguridad, usuario, clave_cifrada, carpeta, activo, "
        "uid_validity, ultimo_uid, ultimo_error, actualizado_en) "
        "ON public.buzon_correo TO iondu_app"
    )
    op.execute("GRANT SELECT ON public.buzon_correo TO iondu_worker")
    op.execute(
        "GRANT UPDATE (uid_validity, ultimo_uid, ultima_lectura, ultimo_error) "
        "ON public.buzon_correo TO iondu_worker"
    )
    op.execute("GRANT SELECT ON public.borrador_gasto TO iondu_app")
    op.execute("GRANT UPDATE (estado, id_gasto) ON public.borrador_gasto TO iondu_app")
    op.execute("GRANT INSERT ON public.borrador_gasto TO iondu_worker")
    # El worker inserta sin RETURNING (no puede leer la tabla): pide el id con nextval.
    op.execute("GRANT USAGE ON SEQUENCE public.borrador_gasto_id_borrador_seq TO iondu_worker")


def downgrade() -> None:
    op.drop_index("idx_borrador_gasto_empresa_estado", table_name="borrador_gasto")
    op.drop_table("borrador_gasto")
    op.drop_table("buzon_correo")
