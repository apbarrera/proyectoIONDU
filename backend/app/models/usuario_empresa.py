import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

ACTIVO = "ACTIVO"
INACTIVO = "INACTIVO"
INVITADO = "INVITADO"


class UsuarioEmpresa(Base):
    __tablename__ = "usuario_empresa"

    __table_args__ = (
        ForeignKeyConstraint(
            ["id_usuario"],
            ["auth.users.id"],
            name="usuario_empresa_id_usuario_fkey",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            f"estado IN ('{ACTIVO}', '{INACTIVO}', '{INVITADO}')",
            name="usuario_empresa_estado_ck",
        ),
        Index("idx_usuario_empresa_empresa", "id_empresa"),
    )

    id_usuario: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    id_empresa: Mapped[int] = mapped_column(
        ForeignKey(
            "empresa.id_empresa",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    id_rol: Mapped[int] = mapped_column(
        ForeignKey(
            "rol.id_rol",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'ACTIVO'"),
    )

    nombre_visible: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
