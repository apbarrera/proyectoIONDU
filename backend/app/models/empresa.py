"""from datetime import datetime
from typing import Any

from sqlalchemy import String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Igual que database/schema.sql. Pendiente (ver docs/ESTADO.md, 2.F): firma .p12
# cifrada y su fecha de vencimiento, y fechas con zona horaria (timestamptz).


class Empresa(Base):
    __tablename__ = "empresa"

    id_empresa: Mapped[int] = mapped_column(primary_key=True)
    razon_social: Mapped[str] = mapped_column(String(255))
    nombre_comercial: Mapped[str | None] = mapped_column(String(255))
    ruc: Mapped[str] = mapped_column(String(13), unique=True)
    actividad_economica: Mapped[str | None] = mapped_column(String(255))
    direccion: Mapped[str | None] = mapped_column(Text)
    correo_electronico: Mapped[str] = mapped_column(String(150))
    datos_facturacion_electronica: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    firma_electronica: Mapped[str | None] = mapped_column(String(255))
    fecha_creacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))"""


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
    datos_facturacion_electronica: Mapped[dict[str, Any] | None] = (
        mapped_column(JSONB)
    )

    certificado_p12_cifrado: Mapped[str | None] = mapped_column(Text)
    certificado_nonce: Mapped[str | None] = mapped_column(String(64))
    certificado_tag: Mapped[str | None] = mapped_column(String(64))
    certificado_password_cifrada: Mapped[str | None] = mapped_column(Text)
    certificado_password_nonce: Mapped[str | None] = mapped_column(
        String(64)
    )
    certificado_password_tag: Mapped[str | None] = mapped_column(
        String(64)
    )
    certificado_fecha_vencimiento: Mapped[date | None] = mapped_column(Date)

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
