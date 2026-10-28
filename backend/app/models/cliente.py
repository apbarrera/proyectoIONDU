
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


class Cliente(Base):
    __tablename__ = "cliente"

    __table_args__ = (
        UniqueConstraint(
            "id_empresa",
            "id_cliente",
            name="cliente_empresa_id_uq",
        ),
        UniqueConstraint(
            "id_empresa",
            "tipo_identificacion",
            "identificacion",
            name="cliente_identificacion_empresa_uq",
        ),
        Index("idx_cliente_empresa", "id_empresa"),
    )

    id_cliente: Mapped[int] = mapped_column(
        Identity(always=False),
        primary_key=True,
    )

    id_empresa: Mapped[int] = mapped_column(
        ForeignKey(
            "empresa.id_empresa",
            ondelete="CASCADE",
            name="cliente_id_empresa_fkey",
        ),
        nullable=False,
    )

    tipo_identificacion: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    identificacion: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    nombre_razon_social: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    direccion: Mapped[str | None] = mapped_column(Text)
    telefono: Mapped[str | None] = mapped_column(String)
    correo_electronico: Mapped[str | None] = mapped_column(String)
