
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.db.base import Base


class Factura(Base):
    __tablename__ = "factura"

    __table_args__ = (
        CheckConstraint(
            "impuestos >= 0",
            name=conv("factura_impuestos_check"),
        ),
        CheckConstraint(
            "numero_comprobante ~ '^[0-9]{3}-[0-9]{3}-[0-9]{9}$'",
            name=conv("factura_numero_formato_ck"),
        ),
        CheckConstraint(
            "subtotal >= 0",
            name=conv("factura_subtotal_check"),
        ),
        CheckConstraint(
            "total >= 0",
            name=conv("factura_total_check"),
        ),
        UniqueConstraint(
            "id_venta",
            name=conv("factura_id_venta_key"),
        ),
        UniqueConstraint(
            "numero_comprobante",
            name=conv("factura_numero_comprobante_key"),
        ),
        UniqueConstraint(
            "clave_acceso",
            name=conv("factura_clave_acceso_key"),
        ),
    )

    id_factura: Mapped[int] = mapped_column(
        Identity(always=False),
        primary_key=True,
    )

    id_venta: Mapped[int] = mapped_column(
        ForeignKey(
            "venta.id_venta",
            ondelete="CASCADE",
            name="factura_id_venta_fkey",
        ),
        nullable=False,
    )

    numero_comprobante: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    clave_acceso: Mapped[str | None] = mapped_column(String)

    estado_autorizacion: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False,
    )

    impuestos: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False,
    )

    total: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False,
    )

    fecha_emision: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    xml_firmado: Mapped[str | None] = mapped_column(Text)

    pdf_ride_path: Mapped[str | None] = mapped_column(String)
