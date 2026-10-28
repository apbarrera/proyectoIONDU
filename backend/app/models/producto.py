from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.db.base import Base

class Producto(Base):
    __tablename__ = "producto"

    __table_args__ = (
        UniqueConstraint(
            "id_empresa",
            "codigo_principal",
            name="producto_codigo_empresa_uq",
        ),
        UniqueConstraint(
            "id_empresa",
            "id_producto",
            name="producto_empresa_id_uq",
        ),
        ForeignKeyConstraint(
            ["id_empresa", "id_categoria_producto"],
            [
                "categoria_producto.id_empresa",
                "categoria_producto.id_categoria_producto",
            ],
            ondelete="RESTRICT",
            name="producto_categoria_empresa_fk",
        ),
        CheckConstraint(
            "precio_compra >= 0",
            name=conv("producto_precio_compra_check"),
        ),
        CheckConstraint(
            "precio_venta >= 0",
            name=conv("producto_precio_venta_check"),
        ),
        CheckConstraint(
            "stock_actual >= 0",
            name=conv("producto_stock_actual_check"),
        ),
        CheckConstraint(
            "stock_minimo IS NULL OR stock_minimo >= 0",
            name=conv("producto_stock_minimo_check"),
        ),
        Index("idx_producto_categoria", "id_categoria_producto"),
        Index("idx_producto_empresa", "id_empresa"),
    )

    id_producto: Mapped[int] = mapped_column(
        Identity(always=False),
        primary_key=True,
    )

    id_empresa: Mapped[int] = mapped_column(
        ForeignKey(
            "empresa.id_empresa",
            ondelete="CASCADE",
            name="producto_id_empresa_fkey",
        ),
        nullable=False,
    )

    id_categoria_producto: Mapped[int] = mapped_column(nullable=False)
    codigo_principal: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)

    precio_compra: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        server_default=text("0"),
    )
    precio_venta: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        server_default=text("0"),
    )
    stock_actual: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        server_default=text("0"),
    )
    stock_minimo: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))

    unidad_medida: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'UNIDAD'"),
    )
    tipo: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'VENTA'"),
    )
    aplica_iva: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
