
from datetime import datetime
from decimal import Decimal
from app.db.base import Base, auth_users

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Numeric,
    String,
    text,
)

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv


class MovimientoInventario(Base):
    __tablename__ = "movimiento_inventario"

    __table_args__ = (
        CheckConstraint(
            "cantidad > 0",
            name=conv("movimiento_inventario_cantidad_check"),
        ),
        Index(
            "idx_movimiento_producto_fecha",
            "id_producto",
            text("fecha DESC"),
        ),
        Index(
            "idx_movimiento_usuario",
            "id_usuario",
        ),
    )

    id_movimiento: Mapped[int] = mapped_column(
        Identity(always=False),
        primary_key=True,
    )

    id_producto: Mapped[int] = mapped_column(
        ForeignKey(
            "producto.id_producto",
            ondelete="CASCADE",
            name="movimiento_inventario_id_producto_fkey",
        ),
        nullable=False,
    )

    id_usuario: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            auth_users.c.id,
            ondelete="RESTRICT",
            name="movimiento_inventario_id_usuario_fkey",
            ),
        nullable=False,
    )

    tipo_movimiento: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    cantidad: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False,
    )

    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    motivo: Mapped[str | None] = mapped_column(String)
