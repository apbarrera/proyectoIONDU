
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ConsumoTokens(Base):
    __tablename__ = "consumo_tokens"


    __table_args__ = (
        CheckConstraint(
            "tokens_prompt >= 0",
            name="tokens_prompt",
        ),
        CheckConstraint(
            "tokens_completado >= 0",
            name="tokens_completado",
        ),
        CheckConstraint(
            "costo_estimado >= 0",
            name="costo_estimado",
        ),
        Index(
            "idx_consumo_tokens_empresa_fecha",
            "id_empresa",
            text("fecha DESC"),
        ),
    )

    id_consumo_tokens: Mapped[int] = mapped_column(
        Integer,
        Identity(always=False),
        primary_key=True,
    )

    id_empresa: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "empresa.id_empresa",
            name="consumo_tokens_id_empresa_fkey",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    modelo_ia: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    tokens_prompt: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    tokens_completado: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    costo_estimado: Mapped[Decimal] = mapped_column(
        Numeric(12, 6),
        nullable=False,
        server_default=text("0"),
    )

    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
