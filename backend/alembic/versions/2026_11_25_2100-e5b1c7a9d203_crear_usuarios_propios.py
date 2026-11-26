"""Crear usuarios y sesiones propios y desligar usuario_empresa de auth.users.

Las pertenencias existentes conservan su UUID: por cada id_usuario de usuario_empresa
se crea un usuario sin contraseña utilizable ("!"). Su correo sale de auth.users si
esa tabla lo tiene (Supabase); si no, queda uno provisional que se corrige con
scripts/crear_usuario.py al asignarle contraseña.

Revision ID: e5b1c7a9d203
Revises: d4e8a2f61c37
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e5b1c7a9d203"
down_revision: str | Sequence[str] | None = "d4e8a2f61c37"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FK_USUARIO = "usuario_empresa_id_usuario_fkey"


def _auth_users_tiene_email(conn) -> bool:
    return (
        conn.execute(
            sa.text(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'auth' AND table_name = 'users' AND column_name = 'email'
                """
            )
        ).first()
        is not None
    )


def upgrade() -> None:
    op.create_table(
        "usuario",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("intentos_fallidos", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("bloqueado_hasta", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint("email = lower(email)", name=op.f("usuario_email_minusculas_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("usuario_pkey")),
        sa.UniqueConstraint("email", name=op.f("usuario_email_key")),
    )
    op.create_table(
        "sesion_refresh",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("id_usuario", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocada_en", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["id_usuario"],
            ["usuario.id"],
            name=op.f("sesion_refresh_id_usuario_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("sesion_refresh_pkey")),
        sa.UniqueConstraint("token_hash", name=op.f("sesion_refresh_token_hash_key")),
    )
    op.create_index("idx_sesion_refresh_usuario", "sesion_refresh", ["id_usuario"])

    # Cada usuario que ya tiene pertenencias pasa a la tabla propia con el mismo UUID.
    conn = op.get_bind()
    if _auth_users_tiene_email(conn):
        correo = "lower(coalesce(au.email, ue.id_usuario::text || '@pendiente.invalid'))"
        origen = "public.usuario_empresa AS ue LEFT JOIN auth.users AS au ON au.id = ue.id_usuario"
    else:
        correo = "ue.id_usuario::text || '@pendiente.invalid'"
        origen = "public.usuario_empresa AS ue"
    op.execute(
        f"""
        INSERT INTO public.usuario (id, email, password_hash)
        SELECT DISTINCT ON (ue.id_usuario) ue.id_usuario, {correo}, '!'
        FROM {origen}
        ON CONFLICT DO NOTHING
        """
    )

    op.drop_constraint(FK_USUARIO, "usuario_empresa", type_="foreignkey")
    op.create_foreign_key(
        FK_USUARIO, "usuario_empresa", "usuario", ["id_usuario"], ["id"], ondelete="CASCADE"
    )

    # La API (iondu_app) busca al usuario por correo ANTES de saber quién es, por eso
    # estas tablas no usan RLS por empresa: el acceso se limita con GRANT por columna.
    # El worker no recibe permisos sobre ellas.
    op.execute("GRANT SELECT ON public.usuario TO iondu_app")
    op.execute(
        "GRANT UPDATE (password_hash, intentos_fallidos, bloqueado_hasta) "
        "ON public.usuario TO iondu_app"
    )
    op.execute("GRANT SELECT, INSERT, DELETE ON public.sesion_refresh TO iondu_app")
    op.execute("GRANT UPDATE (rotada_en, revocada_en) ON public.sesion_refresh TO iondu_app")


def downgrade() -> None:
    # Requiere que exista auth.users con los mismos UUID (Supabase o el marcador local).
    op.drop_constraint(FK_USUARIO, "usuario_empresa", type_="foreignkey")
    op.create_foreign_key(
        FK_USUARIO,
        "usuario_empresa",
        "users",
        ["id_usuario"],
        ["id"],
        referent_schema="auth",
        ondelete="CASCADE",
    )
    op.drop_index("idx_sesion_refresh_usuario", table_name="sesion_refresh")
    op.drop_table("sesion_refresh")
    op.drop_table("usuario")
