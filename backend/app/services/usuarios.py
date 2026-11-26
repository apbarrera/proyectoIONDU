"""Gestión de los usuarios de la empresa (solo Administrador).

Reglas:
- Todo se limita a la empresa de la petición (filtro explícito y RLS).
- Una cuenta (correo) puede pertenecer a varias empresas: si el correo ya existe, solo
  se le agrega la pertenencia y conserva su contraseña.
- El Administrador no puede quitarse a sí mismo el rol ni desactivarse, y la empresa
  nunca se queda sin un Administrador activo.
- Solo se restablece la contraseña de quien trabaja únicamente en esta empresa: si no,
  el Administrador de una empresa podría tomar la cuenta que usa otra.
"""

import secrets
import uuid
from datetime import datetime

from sqlalchemy import func, insert, select, text, update
from sqlalchemy.orm import Session

from app.core import contrasenas
from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.models import Rol, SesionRefresh, Usuario, UsuarioEmpresa
from app.models.rol import ADMINISTRADOR, OPERATIVO
from app.models.usuario_empresa import ACTIVO, INACTIVO
from app.schemas.usuario import CompanyUser, RolApi, UserCreate, UserCreated, UserUpdate
from app.services.autenticacion import normalizar_email

ROL_DESDE_API = {"admin": ADMINISTRADOR, "operator": OPERATIVO}
ROL_HACIA_API: dict[str, RolApi] = {ADMINISTRADOR: "admin", OPERATIVO: "operator"}


def generar_contrasena_temporal() -> str:
    """16 caracteres aleatorios (≈96 bits). Se muestra una sola vez al Administrador."""
    return secrets.token_urlsafe(12)


class UsuarioService:
    def __init__(self, db: Session, empresa_id: int, usuario_actual: uuid.UUID | None):
        self.db = db
        self.empresa_id = empresa_id
        self.actual_id = usuario_actual

    # ---------- Consultas ----------
    def listar(self) -> list[CompanyUser]:
        filas = self.db.execute(self._consulta().order_by(func.lower(Usuario.email))).all()
        return [self._a_api(*fila) for fila in filas]

    def obtener(self, id_usuario: uuid.UUID) -> CompanyUser:
        fila = self.db.execute(
            self._consulta().where(UsuarioEmpresa.id_usuario == id_usuario)
        ).first()
        if fila is None:
            raise NotFoundError("El usuario no pertenece a esta empresa.", code="USER_NOT_FOUND")
        return self._a_api(*fila)

    # ---------- Crear ----------
    def crear(self, datos: UserCreate) -> UserCreated:
        email = normalizar_email(datos.email)
        local, arroba, dominio = email.partition("@")
        if not (local and arroba and "." in dominio):
            raise UnprocessableError("El correo no es válido.", code="INVALID_EMAIL")

        id_usuario = self.db.scalar(select(Usuario.id).where(Usuario.email == email))
        contrasena: str | None = None
        if id_usuario is None:
            contrasena = generar_contrasena_temporal()
            id_usuario = uuid.uuid4()
            # INSERT explícito con solo estas columnas: es lo único que iondu_app puede
            # insertar en `usuario` (el ORM agregaría bloqueado_hasta = NULL).
            self.db.execute(
                insert(Usuario).values(
                    id=id_usuario, email=email, password_hash=contrasenas.hashear(contrasena)
                )
            )
        elif self.db.get(UsuarioEmpresa, (id_usuario, self.empresa_id)) is not None:
            raise ConflictError(
                "Ese correo ya es usuario de esta empresa. Búscalo en la lista para editarlo.",
                code="USER_ALREADY_MEMBER",
            )

        self.db.add(
            UsuarioEmpresa(
                id_usuario=id_usuario,
                id_empresa=self.empresa_id,
                id_rol=self._id_rol(datos.role),
                nombre_visible=datos.full_name.strip(),
                estado=ACTIVO,
            )
        )
        self.db.commit()
        return UserCreated(user=self.obtener(id_usuario), temporary_password=contrasena)

    # ---------- Editar ----------
    def actualizar(self, id_usuario: uuid.UUID, datos: UserUpdate) -> CompanyUser:
        pertenencia = self._pertenencia(id_usuario)
        rol_actual = self.db.scalar(select(Rol.nombre).where(Rol.id_rol == pertenencia.id_rol))
        rol_nuevo = ROL_DESDE_API[datos.role] if datos.role is not None else rol_actual

        if id_usuario == self.actual_id and (rol_nuevo != rol_actual or datos.active is False):
            raise ConflictError(
                "No puedes cambiar tu propio rol ni desactivarte.", code="CANNOT_MODIFY_SELF"
            )

        deja_de_ser_admin_activo = (
            rol_actual == ADMINISTRADOR
            and pertenencia.estado == ACTIVO
            and (rol_nuevo != ADMINISTRADOR or datos.active is False)
        )
        if deja_de_ser_admin_activo and self._administradores_activos() <= 1:
            raise ConflictError(
                "La empresa debe tener al menos un Administrador activo.", code="LAST_ADMIN"
            )

        if datos.full_name is not None:
            pertenencia.nombre_visible = datos.full_name.strip()
        if datos.role is not None:
            pertenencia.id_rol = self._id_rol(datos.role)
        if datos.active is not None:
            pertenencia.estado = ACTIVO if datos.active else INACTIVO
        self.db.commit()
        return self.obtener(id_usuario)

    # ---------- Restablecer contraseña ----------
    def restablecer_contrasena(self, id_usuario: uuid.UUID) -> str:
        self._pertenencia(id_usuario)
        if id_usuario == self.actual_id:
            raise ConflictError(
                "Para cambiar tu contraseña usa Preferencias > Cambiar contraseña.",
                code="CANNOT_MODIFY_SELF",
            )
        if self._en_otras_empresas(id_usuario):
            raise ConflictError(
                "Este usuario también trabaja en otra empresa: solo él puede cambiar su "
                "contraseña.",
                code="USER_IN_OTHER_COMPANY",
            )

        usuario = self.db.get(Usuario, id_usuario, with_for_update=True)
        contrasena = generar_contrasena_temporal()
        usuario.password_hash = contrasenas.hashear(contrasena)
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        # La contraseña anterior deja de servir también en las sesiones abiertas.
        self.db.execute(
            update(SesionRefresh)
            .where(SesionRefresh.id_usuario == id_usuario, SesionRefresh.revocada_en.is_(None))
            .values(revocada_en=func.now())
        )
        self.db.commit()
        return contrasena

    # ---------- Internos ----------
    def _consulta(self):
        return (
            select(
                Usuario.id,
                Usuario.email,
                UsuarioEmpresa.nombre_visible,
                Rol.nombre,
                UsuarioEmpresa.estado,
                UsuarioEmpresa.fecha_creacion,
            )
            .join(UsuarioEmpresa, UsuarioEmpresa.id_usuario == Usuario.id)
            .join(Rol, Rol.id_rol == UsuarioEmpresa.id_rol)
            .where(UsuarioEmpresa.id_empresa == self.empresa_id)
        )

    @staticmethod
    def _a_api(
        id_usuario: uuid.UUID,
        email: str,
        nombre: str | None,
        rol: str,
        estado: str,
        creado: datetime,
    ) -> CompanyUser:
        return CompanyUser(
            id=id_usuario,
            email=email,
            full_name=nombre or email,
            role=ROL_HACIA_API.get(rol, "operator"),
            active=estado == ACTIVO,
            created_at=creado,
        )

    def _pertenencia(self, id_usuario: uuid.UUID) -> UsuarioEmpresa:
        pertenencia = self.db.get(
            UsuarioEmpresa, (id_usuario, self.empresa_id), with_for_update=True
        )
        if pertenencia is None:
            raise NotFoundError("El usuario no pertenece a esta empresa.", code="USER_NOT_FOUND")
        return pertenencia

    def _id_rol(self, rol: RolApi) -> int:
        nombre = ROL_DESDE_API[rol]
        id_rol = self.db.scalar(select(Rol.id_rol).where(Rol.nombre == nombre))
        if id_rol is None:
            raise UnprocessableError(f"No existe el rol {nombre}.", code="ROLE_NOT_FOUND")
        return id_rol

    def _administradores_activos(self) -> int:
        return self.db.scalar(
            select(func.count())
            .select_from(UsuarioEmpresa)
            .join(Rol, Rol.id_rol == UsuarioEmpresa.id_rol)
            .where(
                UsuarioEmpresa.id_empresa == self.empresa_id,
                UsuarioEmpresa.estado == ACTIVO,
                Rol.nombre == ADMINISTRADOR,
            )
        )

    def _en_otras_empresas(self, id_usuario: uuid.UUID) -> bool:
        # Función SECURITY DEFINER: el Administrador no ve las pertenencias de otras empresas.
        return bool(
            self.db.scalar(
                text("SELECT public.app_usuario_en_otras_empresas(:usuario, :empresa)"),
                {"usuario": id_usuario, "empresa": self.empresa_id},
            )
        )
