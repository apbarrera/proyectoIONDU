
from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AccionIA(Base):
    __tablename__ = "accion_ia"

    id_accion_ia: Mapped[int] = mapped_column(
        Integer,
        Identity(always=False),
        primary_key=True,
    )

    id_empresa: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.id_empresa", ondelete="CASCADE"),
        nullable=False,
    )

    id_usuario: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    tipo_accion: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    instruccion_recibida: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    payload_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'PENDIENTE'"),
    )

    fecha: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["id_usuario", "id_empresa"],
            ["usuario_empresa.id_usuario", "usuario_empresa.id_empresa"],
            name="accion_ia_usuario_empresa_fk",
            ondelete="SET NULL (id_usuario)",
        ),
        Index(
            "idx_accion_ia_empresa_fecha",
            "id_empresa",
            text("fecha DESC"),
        ),
    )
