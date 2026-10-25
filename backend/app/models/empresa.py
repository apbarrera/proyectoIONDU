from datetime import datetime
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
    fecha_creacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
