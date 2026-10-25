from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Igual que database/schema.sql. Pendiente (ver docs/ESTADO.md, 2.F): columna
# "activo", UNIQUE (id_empresa, codigo_principal), CHECK de no negativos e índices.


class Producto(Base):
    __tablename__ = "producto"

    id_producto: Mapped[int] = mapped_column(primary_key=True)
    id_empresa: Mapped[int] = mapped_column(
        ForeignKey("empresa.id_empresa", onupdate="CASCADE", ondelete="CASCADE")
    )
    id_categoria_producto: Mapped[int] = mapped_column(
        ForeignKey(
            "categoria_producto.id_categoria_producto", onupdate="CASCADE", ondelete="RESTRICT"
        )
    )
    codigo_principal: Mapped[str] = mapped_column(String(50))
    nombre: Mapped[str] = mapped_column(String(150))
    descripcion: Mapped[str | None] = mapped_column(Text)
    precio_compra: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default=text("0.00"))
    precio_venta: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default=text("0.00"))
    stock_actual: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default=text("0.00"))
    stock_minimo: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    unidad_medida: Mapped[str] = mapped_column(String(20), server_default=text("'UNIDAD'"))
    tipo: Mapped[str] = mapped_column(String(20), server_default=text("'VENTA'"))
    aplica_iva: Mapped[bool] = mapped_column(server_default=text("true"))
