
from sqlalchemy import (
    ForeignKey,
    Identity,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CategoriaGasto(Base):
    __tablename__ = "categoria_gasto"

    __table_args__ = (
        UniqueConstraint(
            "id_empresa",
            "id_categoria_gasto",
            name="categoria_gasto_empresa_id_uq",
        ),
        UniqueConstraint(
            "id_empresa",
            "nombre",
            name="categoria_gasto_nombre_uq",
        ),
    )

    id_categoria_gasto: Mapped[int] = mapped_column(
        Identity(always=False),
        primary_key=True,
    )

    id_empresa: Mapped[int] = mapped_column(
        ForeignKey(
            "empresa.id_empresa",
            ondelete="CASCADE",
            name="categoria_gasto_id_empresa_fkey",
        ),
        nullable=False,
    )

    nombre: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    origen: Mapped[str] = mapped_column(
        String,
        nullable=False,
        server_default=text("'PREDEFINIDA'"),
    )

    descripcion: Mapped[str | None] = mapped_column(String)
