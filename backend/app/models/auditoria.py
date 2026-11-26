import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

MODULOS = (
    "auth",
    "ventas",
    "facturacion",
    "gastos",
    "inventario",
    "ia",
    "configuracion",
    "usuarios",
)


class Auditoria(Base):
    """Registro de actividad de la empresa. Solo se inserta: nadie lo edita ni lo borra."""

    __tablename__ = "auditoria"

    __table_args__ = (
        CheckConstraint("modulo IN (" + ", ".join(f"'{m}'" for m in MODULOS) + ")", name="modulo"),
        Index("idx_auditoria_empresa_fecha", "id_empresa", "fecha"),
    )

    id_auditoria: Mapped[int] = mapped_column(Identity(always=False), primary_key=True)
    id_empresa: Mapped[int] = mapped_column(
        ForeignKey("empresa.id_empresa", ondelete="RESTRICT"), nullable=False
    )
    # Si la cuenta se borra, el registro se conserva sin autor.
    id_usuario: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="SET NULL")
    )
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    modulo: Mapped[str] = mapped_column(String(20), nullable=False)
    accion: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    # Qué se tocó (p. ej., "venta" y su id), para enlazar o filtrar más adelante.
    entidad: Mapped[str | None] = mapped_column(String(50))
    id_entidad: Mapped[str | None] = mapped_column(String(50))
