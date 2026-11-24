from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Identity,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.db.base import Base


class Empresa(Base):
    __tablename__ = "empresa"

    __table_args__ = (
        UniqueConstraint("ruc", name="empresa_ruc_key"),
        CheckConstraint(
            "ruc ~ '^[0-9]{13}$'",
            name=conv("empresa_ruc_formato"),
        ),
        CheckConstraint(
            """
            (
                certificado_p12_cifrado IS NULL
                AND certificado_password_cifrada IS NULL
            )
            OR
            (
                certificado_p12_cifrado IS NOT NULL
                AND certificado_password_cifrada IS NOT NULL
            )
            """,
            name=conv("empresa_certificado_par_check"),
        ),
    )

    id_empresa: Mapped[int] = mapped_column(
        Identity(always=False),
        primary_key=True,
    )

    razon_social: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    nombre_comercial: Mapped[str | None] = mapped_column(String(255))
    ruc: Mapped[str] = mapped_column(String(13), nullable=False)
    actividad_economica: Mapped[str | None] = mapped_column(String(255))
    direccion: Mapped[str | None] = mapped_column(Text)
    correo_electronico: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    datos_facturacion_electronica: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    certificado_p12_cifrado: Mapped[str | None] = mapped_column(Text)
    certificado_password_cifrada: Mapped[str | None] = mapped_column(Text)
    certificado_fecha_vencimiento: Mapped[date | None] = mapped_column(Date)

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
