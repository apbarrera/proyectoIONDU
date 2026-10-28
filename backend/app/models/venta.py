
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.db.base import Base


class Venta(Base):
    __tablename__ = "venta"

    __table_args__ = (
        UniqueConstraint(
            "id_empresa",
            "id_venta",
            name="venta_empresa_id_uq",
        ),
        CheckConstraint(
            "iva >= 0",
            name=conv("venta_iva_check"),
        ),
        CheckConstraint(
            "monto_total >= 0",
            name=conv("venta_monto_total_check"),
        ),
        CheckConstraint(
            "subtotal >= 0",
            name=conv("venta_subtotal_check"),
        ),
        ForeignKeyConstraint(
            ["id_empresa", "id_cliente"],
            ["cliente.id_empresa", "cliente.id_cliente"],
            ondelete="SET NULL (id_cliente)",
            name="venta_cliente_empresa_fk",
        ),
        ForeignKeyConstraint(
            ["id_usuario", "id_empresa"],
            [
                "usuario_empresa.id_usuario",
                "usuario_empresa.id_empresa",
            ],
            ondelete="RESTRICT",
            name="venta_usuario_empresa_fk",
        ),
        Index("idx_venta_cliente", "id_cliente"),
        Index(
            "idx_venta_empresa_fecha",
            "id_empresa",
            text("fecha DESC"),
        ),
        Index("idx_venta_usuario", "id_usuario"),
    )

    id_venta: Mapped[int] = mapped_column(
        Identity(always=False),
        primary_key=True,
    )

    id_empresa: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "empresa.id_empresa",
            ondelete="CASCADE",
            name="venta_id_empresa_fkey",
        ),
        nullable=False,
    )

    id_usuario: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )

    id_cliente: Mapped[int | None] = mapped_column(Integer)

    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    iva: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    monto_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    tipo_origen: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    metodo_pago: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    observacion: Mapped[str | None] = mapped_column(String(255))

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'COMPLETADA'"),
    )
