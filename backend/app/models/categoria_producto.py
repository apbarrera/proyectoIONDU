"""from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CategoriaProducto(Base):
    __tablename__ = "categoria_producto"

    id_categoria_producto: Mapped[int] = mapped_column(primary_key=True)
    id_empresa: Mapped[int] = mapped_column(
        ForeignKey("empresa.id_empresa", onupdate="CASCADE", ondelete="CASCADE")
    )
    nombre: Mapped[str] = mapped_column(String(100))
    descripcion: Mapped[str | None] = mapped_column(String(255))"""

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Identity
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CategoriaProducto(Base):
    __tablename__ = "categoria_producto"

    __table_args__ = (
        UniqueConstraint(
            "id_empresa",
            "id_categoria_producto",
            name="categoria_producto_empresa_id_uq",
        ),
        UniqueConstraint(
            "id_empresa",
            "nombre",
            name="categoria_producto_nombre_uq",
        ),
    )

    id_categoria_producto: Mapped[int] = mapped_column(
    Identity(always=False),
    primary_key=True,
)
    id_empresa: Mapped[int] = mapped_column(
        ForeignKey(
            "empresa.id_empresa",
            ondelete="CASCADE",
            name="categoria_producto_id_empresa_fkey",
        ),
        nullable=False,
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255))
