"""Usuarios de la empresa: solo el Administrador (docs/API.md, sección 5)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Response

from app.api.deps import DbSession, SoloAdministrador
from app.schemas.usuario import CompanyUser, PasswordReset, UserCreate, UserCreated, UserUpdate
from app.services.usuarios import UsuarioService

router = APIRouter(prefix="/users", tags=["Usuarios"])

UserId = Annotated[UUID, Path()]


def _servicio(db: DbSession, contexto: SoloAdministrador) -> UsuarioService:
    usuario = contexto.usuario.id if contexto.usuario else None
    return UsuarioService(db, contexto.empresa_id, usuario)


@router.get("", response_model=list[CompanyUser])
def list_users(contexto: SoloAdministrador, db: DbSession):
    return _servicio(db, contexto).listar()


@router.post("", response_model=UserCreated, status_code=201)
def create_user(datos: UserCreate, response: Response, contexto: SoloAdministrador, db: DbSession):
    # La respuesta puede traer la contraseña temporal: que nadie la guarde en caché.
    response.headers["Cache-Control"] = "no-store"
    return _servicio(db, contexto).crear(datos)


@router.patch("/{id}", response_model=CompanyUser)
def update_user(id: UserId, datos: UserUpdate, contexto: SoloAdministrador, db: DbSession):
    return _servicio(db, contexto).actualizar(id, datos)


@router.post("/{id}/reset-password", response_model=PasswordReset)
def reset_password(id: UserId, response: Response, contexto: SoloAdministrador, db: DbSession):
    response.headers["Cache-Control"] = "no-store"
    return PasswordReset(temporary_password=_servicio(db, contexto).restablecer_contrasena(id))
