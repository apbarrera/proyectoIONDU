"""Correo de facturas de proveedores (RF-3.2, RF-3.3)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

PENDIENTE = "PENDIENTE"
CONVERTIDO = "CONVERTIDO"
DESCARTADO = "DESCARTADO"


class BuzonCorreo(Base):
    """Cuenta IMAP de la empresa donde llegan las facturas de sus proveedores."""

    __tablename__ = "buzon_correo"

    __table_args__ = (
        CheckConstraint("puerto BETWEEN 1 AND 65535", name="buzon_correo_puerto_check"),
        CheckConstraint(
            "seguridad IN ('ssl', 'starttls', 'ninguna')", name="buzon_correo_seguridad_check"
        ),
    )

    id_empresa: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.id_empresa", ondelete="CASCADE"),
        primary_key=True,
    )
    servidor: Mapped[str] = mapped_column(String(255), nullable=False)
    puerto: Mapped[int] = mapped_column(Integer, nullable=False)
    seguridad: Mapped[str] = mapped_column(String(10), nullable=False, server_default=text("'ssl'"))
    usuario: Mapped[str] = mapped_column(String(254), nullable=False)
    # Clave cifrada con MASTER_ENCRYPTION_KEY (base64); solo el worker la descifra.
    clave_cifrada: Mapped[str] = mapped_column(Text, nullable=False)
    carpeta: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default=text("'INBOX'")
    )
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    # Hasta dónde se leyó: si UIDVALIDITY cambia, se vuelve a leer (sin duplicar).
    uid_validity: Mapped[int | None] = mapped_column(BigInteger)
    ultimo_uid: Mapped[int | None] = mapped_column(BigInteger)
    ultima_lectura: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ultimo_error: Mapped[str | None] = mapped_column(String(300))
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class BorradorGasto(Base):
    """Factura encontrada en el correo, pendiente de que el usuario la confirme."""

    __tablename__ = "borrador_gasto"

    __table_args__ = (
        UniqueConstraint("id_empresa", "message_id", name="borrador_gasto_empresa_message_uq"),
        UniqueConstraint("id_empresa", "clave_acceso", name="borrador_gasto_empresa_clave_uq"),
        CheckConstraint(
            "estado IN ('PENDIENTE', 'CONVERTIDO', 'DESCARTADO')",
            name="borrador_gasto_estado_check",
        ),
        Index("idx_borrador_gasto_empresa_estado", "id_empresa", "estado"),
        # El worker solo puede INSERTAR (sin SELECT): nada de RETURNING al insertar.
        {"implicit_returning": False},
    )

    id_borrador: Mapped[int] = mapped_column(Identity(always=False), primary_key=True)
    id_empresa: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresa.id_empresa", ondelete="CASCADE"), nullable=False
    )
    message_id: Mapped[str] = mapped_column(String(998), nullable=False)
    clave_acceso: Mapped[str | None] = mapped_column(String(49))
    remitente: Mapped[str | None] = mapped_column(String(254))
    asunto: Mapped[str | None] = mapped_column(String(300))
    recibido_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    proveedor_ruc: Mapped[str | None] = mapped_column(String(13))
    proveedor_nombre: Mapped[str | None] = mapped_column(String(300))
    numero_comprobante: Mapped[str | None] = mapped_column(String(20))
    fecha_emision: Mapped[date | None] = mapped_column(Date)
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    iva: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    detalle: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    estado: Mapped[str] = mapped_column(
        String(15), nullable=False, server_default=text("'PENDIENTE'")
    )
    id_gasto: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("gasto.id_gasto", ondelete="SET NULL")
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
