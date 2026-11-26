import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Usuario(Base):
    """Cuenta de acceso al sistema (identidad). Las empresas y el rol viven en usuario_empresa."""

    __tablename__ = "usuario"

    __table_args__ = (CheckConstraint("email = lower(email)", name="email_minusculas"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    # Siempre en minúsculas; la unicidad es sobre el correo normalizado.
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    # Hash argon2id. Nunca la contraseña. "!" marca una cuenta sin contraseña utilizable.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    intentos_fallidos: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class SesionRefresh(Base):
    """Token de renovación de sesión. Solo se guarda su hash SHA-256."""

    __tablename__ = "sesion_refresh"

    __table_args__ = (Index("idx_sesion_refresh_usuario", "id_usuario"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    id_usuario: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Se llena al rotar el token; permite una breve ventana de gracia para peticiones simultáneas.
    rotada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revocada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
