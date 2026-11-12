from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.db.base import Base


class DetalleVenta(Base):
    __tablename__ = "detalle_venta"

    __table_args__ = (
        ForeignKeyConstraint(
            ["id_empresa", "id_venta"],
            ["venta.id_empresa", "venta.id_venta"],
            ondelete="CASCADE",
            name="detalle_venta_empresa_venta_fk",
        ),
        ForeignKeyConstraint(
            ["id_empresa", "id_producto"],
            ["producto.id_empresa", "producto.id_producto"],
            ondelete="SET NULL (id_producto)",
            name="detalle_venta_empresa_producto_fk",
        ),
        CheckConstraint(
            "cantidad > 0",
            name=conv("detalle_venta_cantidad_check"),
        ),
        CheckConstraint(
            "descuento >= 0",
            name=conv("detalle_venta_descuento_check"),
        ),
        CheckConstraint(
            "precio_unitario >= 0",
            name=conv("detalle_venta_precio_unitario_check"),
        ),
        CheckConstraint(
            "id_producto IS NOT NULL OR descripcion_libre IS NOT NULL",
            name=conv("detalle_venta_producto_o_descripcion_ck"),
        ),
        CheckConstraint(
            "codigo_porcentaje_iva IN ('0', '4', '5', '6', '7')",
            name=conv("detalle_venta_codigo_iva_check"),
        ),
        CheckConstraint(
            "subtotal >= 0",
            name=conv("detalle_venta_subtotal_check"),
        ),
        Index("idx_detalle_venta_producto", "id_producto"),
        Index("idx_detalle_venta_venta", "id_venta"),
    )

    id_detalle_venta: Mapped[int] = mapped_column(
        Identity(always=False),
        primary_key=True,
    )

    id_empresa: Mapped[int] = mapped_column(Integer, nullable=False)

    id_venta: Mapped[int] = mapped_column(Integer, nullable=False)

    id_producto: Mapped[int | None] = mapped_column(Integer)

    descripcion_libre: Mapped[str | None] = mapped_column(String(255))

    cantidad: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
    )

    precio_unitario: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
    )

    descuento: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        server_default=text("0"),
    )

    codigo_porcentaje_iva: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
