from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Identity,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.db.base import Base


class SecuenciaComprobante(Base):
    __tablename__ = "secuencia_comprobante"

    __table_args__ = (
        CheckConstraint(
            "establecimiento ~ '^[0-9]{3}$'",
            name=conv("secuencia_comprobante_establecimiento_ck"),
        ),
        CheckConstraint(
            "punto_emision ~ '^[0-9]{3}$'",
            name=conv("secuencia_comprobante_punto_emision_ck"),
        ),
        CheckConstraint(
            "tipo_comprobante ~ '^[0-9]{2}$'",
            name=conv("secuencia_comprobante_tipo_ck"),
        ),
        CheckConstraint(
            "ultimo_secuencial BETWEEN 0 AND 999999999",
            name=conv("secuencia_comprobante_ultimo_ck"),
        ),
        UniqueConstraint(
            "id_empresa",
            "establecimiento",
            "punto_emision",
            "tipo_comprobante",
            name="secuencia_comprobante_configuracion_uq",
        ),
    )

    id_secuencia: Mapped[int] = mapped_column(
        Identity(always=False),
        primary_key=True,
    )

    id_empresa: Mapped[int] = mapped_column(
        ForeignKey(
            "empresa.id_empresa",
            ondelete="RESTRICT",
            name="secuencia_comprobante_id_empresa_fkey",
        ),
        nullable=False,
    )

    establecimiento: Mapped[str] = mapped_column(String(3), nullable=False)

    punto_emision: Mapped[str] = mapped_column(String(3), nullable=False)

    tipo_comprobante: Mapped[str] = mapped_column(String(2), nullable=False)

    ultimo_secuencial: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text("0"),
    )
