import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Diseño acordado (docs/DECISIONES.md 2.3 y CORRECCIONES_PDF.md B); reemplaza a la
# tabla "usuario" con contraseñas propias. AÚN NO EXISTE en database/schema.sql: la
# creará la migración del esquema corregido. Si Ariana cambia algún nombre o tipo,
# se ajusta aquí.
#
# id_usuario es el UUID del usuario en Supabase Auth (auth.users.id). Esa relación
# no se declara en Python porque auth.users vive en otro esquema de la base; la
# agregará la migración.

ACTIVO = "ACTIVO"


class UsuarioEmpresa(Base):
    __tablename__ = "usuario_empresa"
    # Gasto, venta y accion_ia apuntan a (id_usuario, id_empresa) para que la base
    # impida registrar algo con un usuario de otra empresa; PostgreSQL exige que esa
    # pareja esté declarada como única (lo es: id_usuario ya es la clave primaria).
    __table_args__ = (UniqueConstraint("id_usuario", "id_empresa"),)

    id_usuario: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    id_empresa: Mapped[int] = mapped_column(
        ForeignKey("empresa.id_empresa", onupdate="CASCADE", ondelete="CASCADE")
    )
    id_rol: Mapped[int] = mapped_column(
        ForeignKey("rol.id_rol", onupdate="CASCADE", ondelete="RESTRICT")
    )
    nombre: Mapped[str] = mapped_column(String(150))
    estado: Mapped[str] = mapped_column(String(20), server_default=text(f"'{ACTIVO}'"))
