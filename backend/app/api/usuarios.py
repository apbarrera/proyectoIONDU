"""Usuarios de la empresa: solo el Administrador (docs/API.md, sección 5)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Path, Response
from sqlalchemy import select

from app.api.auth import EnviadorActual
from app.api.deps import AuditorActual, AuthDbSession, DbSession, SoloAdministrador
from app.core.config import get_settings
from app.core.correo import enviar_sin_fallar
from app.models import Empresa, Usuario
from app.schemas.usuario import CompanyUser, PasswordReset, UserCreate, UserCreated, UserUpdate
from app.services.recuperacion import INVITACION, ServicioRecuperacion, correo_invitacion
from app.services.usuarios import UsuarioService

router = APIRouter(prefix="/users", tags=["Usuarios"])

UserId = Annotated[UUID, Path()]
ROLES = {"admin": "Administrador", "operator": "Operativo"}


def _servicio(
    db: DbSession, contexto: SoloAdministrador, auth_db: AuthDbSession | None = None
) -> UsuarioService:
    usuario = contexto.usuario.id if contexto.usuario else None
    return UsuarioService(db, contexto.empresa_id, usuario, auth_db=auth_db)


@router.get("", response_model=list[CompanyUser])
def list_users(contexto: SoloAdministrador, db: DbSession):
    return _servicio(db, contexto).listar()


@router.post("", response_model=UserCreated, status_code=201)
def create_user(
    datos: UserCreate,
    response: Response,
    contexto: SoloAdministrador,
    db: DbSession,
    auth_db: AuthDbSession,
    auditor: AuditorActual,
    enviador: EnviadorActual,
    tareas: BackgroundTasks,
):
    # La respuesta puede traer la contraseña temporal: que nadie la guarde en caché.
    response.headers["Cache-Control"] = "no-store"
    creado = _servicio(db, contexto, auth_db).crear(datos)
    cuenta = "cuenta nueva" if creado.temporary_password else "cuenta existente"

    # Cuenta nueva y correo configurado: además de la contraseña temporal, se envía
    # un enlace para que la persona elija su propia contraseña.
    if enviador is not None and creado.temporary_password:
        # iondu_app solo puede leer id y email de usuario. No cargar el modelo completo.
        usuario = Usuario(id=creado.user.id, email=creado.user.email)
        enlace = ServicioRecuperacion(auth_db).crear_enlace(usuario, INVITACION)

        # Consultar únicamente la columna permitida/necesaria.
        nombre_empresa = (
            db.scalar(select(Empresa.razon_social).where(Empresa.id_empresa == contexto.empresa_id))
            or "tu empresa"
        )

        correo = correo_invitacion(
            get_settings().app_public_url,
            enlace.token,
            nombre_empresa,
            creado.user.full_name,
        )
        tareas.add_task(
            enviar_sin_fallar,
            enviador,
            enlace.destinatario,
            correo.asunto,
            correo.texto,
            correo.html,
        )
        creado = creado.model_copy(update={"invitation_sent": True})

    auditor.registrar(
        "usuarios",
        "Creó usuario",
        f"{creado.user.full_name} ({creado.user.email}) como {ROLES[creado.user.role]}, {cuenta}.",
        entidad="usuario",
        id_entidad=creado.user.id,
    )
    return creado


@router.patch("/{id}", response_model=CompanyUser)
def update_user(
    id: UserId,
    datos: UserUpdate,
    contexto: SoloAdministrador,
    db: DbSession,
    auditor: AuditorActual,
):
    usuario = _servicio(db, contexto).actualizar(id, datos)
    cambios = []
    if datos.full_name is not None:
        cambios.append("nombre")
    if datos.role is not None:
        cambios.append(f"rol {ROLES[usuario.role]}")
    if datos.active is not None:
        cambios.append("activado" if usuario.active else "desactivado")
    auditor.registrar(
        "usuarios",
        "Editó usuario",
        f"{usuario.full_name}: {', '.join(cambios) or 'sin cambios'}.",
        entidad="usuario",
        id_entidad=id,
    )
    return usuario


@router.post("/{id}/reset-password", response_model=PasswordReset)
def reset_password(
    id: UserId,
    response: Response,
    contexto: SoloAdministrador,
    db: DbSession,
    auth_db: AuthDbSession,
    auditor: AuditorActual,
):
    response.headers["Cache-Control"] = "no-store"
    servicio = _servicio(db, contexto, auth_db)
    temporal = servicio.restablecer_contrasena(id)
    # La contraseña temporal nunca se guarda en la auditoría.
    auditor.registrar(
        "usuarios",
        "Restableció contraseña",
        f"De {servicio.obtener(id).full_name}; se cerraron sus sesiones.",
        entidad="usuario",
        id_entidad=id,
    )
    return PasswordReset(temporary_password=temporal)
