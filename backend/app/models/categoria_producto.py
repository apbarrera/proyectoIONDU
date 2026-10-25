from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CategoriaProducto(Base):
    __tablename__ = "categoria_producto"

    id_categoria_producto: Mapped[int] = mapped_column(primary_key=True)
    id_empresa: Mapped[int] = mapped_column(
        ForeignKey("empresa.id_empresa", onupdate="CASCADE", ondelete="CASCADE")
    )
    nombre: Mapped[str] = mapped_column(String(100))
    descripcion: Mapped[str | None] = mapped_column(String(255))
