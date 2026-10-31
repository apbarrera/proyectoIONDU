from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.db.base import Base


class MovimientoInventario(Base):
    __tablename__ = "movimiento_inventario"

    __table_args__ = (
        ForeignKeyConstraint(
            ["id_empresa", "id_producto"],
            ["producto.id_empresa", "producto.id_producto"],
            name="movimiento_inventario_empresa_producto_fkey",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["id_usuario", "id_empresa"],
            ["usuario_empresa.id_usuario", "usuario_empresa.id_empresa"],
            name="movimiento_inventario_usuario_empresa_fkey",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "cantidad > 0",
            name=conv("movimiento_inventario_cantidad_check"),
        ),
        Index(
            "idx_movimiento_producto_fecha",
            "id_producto",
            text("fecha DESC"),
        ),
        Index("idx_movimiento_usuario", "id_usuario"),
        Index("idx_movimiento_empresa", "id_empresa"),
    )

    id_movimiento: Mapped[int] = mapped_column(
        Identity(always=False),
        primary_key=True,
    )

    id_empresa: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    id_producto: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    id_usuario: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    tipo_movimiento: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    cantidad: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
    )

    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    motivo: Mapped[str | None] = mapped_column(String)
