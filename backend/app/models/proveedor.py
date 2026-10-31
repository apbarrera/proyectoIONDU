from sqlalchemy import (
    ForeignKey,
    Identity,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Proveedor(Base):
    __tablename__ = "proveedor"

    __table_args__ = (
        UniqueConstraint(
            "id_empresa",
            "id_proveedor",
            name="proveedor_empresa_id_uq",
        ),
        UniqueConstraint(
            "id_empresa",
            "ruc_identificacion",
            name="proveedor_identificacion_empresa_uq",
        ),
        Index("idx_proveedor_empresa", "id_empresa"),
    )

    id_proveedor: Mapped[int] = mapped_column(
        Identity(always=False),
        primary_key=True,
    )

    id_empresa: Mapped[int] = mapped_column(
        ForeignKey(
            "empresa.id_empresa",
            ondelete="CASCADE",
            name="proveedor_id_empresa_fkey",
        ),
        nullable=False,
    )

    ruc_identificacion: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    razon_social: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    telefono: Mapped[str | None] = mapped_column(String)
    correo_electronico: Mapped[str | None] = mapped_column(String)
    direccion: Mapped[str | None] = mapped_column(Text)
