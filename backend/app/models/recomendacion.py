from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Recomendacion(Base):
    __tablename__ = "recomendacion"

    __table_args__ = (
        Index(
            "idx_recomendacion_empresa_fecha",
            "id_empresa",
            text("fecha DESC"),
        ),
    )

    id_recomendacion: Mapped[int] = mapped_column(
        Identity(always=False),
        primary_key=True,
    )

    id_empresa: Mapped[int] = mapped_column(
        ForeignKey(
            "empresa.id_empresa",
            name="recomendacion_id_empresa_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    tipo: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    descripcion: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    datos_utilizados: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'ACTIVA'"),
    )

    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
