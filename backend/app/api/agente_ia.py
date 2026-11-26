"""Agente de IA (docs/API.md, sección 15). Cualquier usuario de la empresa lo usa."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.deps import AuditorActual, ContextoActual, DbSession
from app.core.config import get_settings
from app.core.errors import ForbiddenError
from app.ia.cliente import ClienteOpenAICompatible, ModeloLenguaje
from app.schemas.agente_ia import (
    AiAction,
    AiConfirm,
    AiConfirmResult,
    AiMessageInput,
    AiReply,
)
from app.schemas.common import Page
from app.services.agente_ia import ESTADOS_API, ServicioAgente

router = APIRouter(prefix="/ai", tags=["Agente IA"])

ActionId = Annotated[int, Path(gt=0)]


def get_modelo() -> ModeloLenguaje | None:
    """Cliente del modelo según LLM_*; None si no está configurado. Las pruebas lo reemplazan."""
    settings = get_settings()
    if not settings.llm_base_url:
        return None
    return ClienteOpenAICompatible(
        settings.llm_base_url,
        settings.llm_model,
        settings.llm_api_key.get_secret_value() if settings.llm_api_key else None,
        settings.llm_timeout_seconds,
    )


Modelo = Annotated[ModeloLenguaje | None, Depends(get_modelo)]


def _servicio(db, contexto, modelo=None) -> ServicioAgente:
    # Las acciones del agente quedan a nombre de un usuario real.
    if contexto.usuario is None:
        raise ForbiddenError(
            "Para usar el agente de IA debes iniciar sesión con tu usuario.",
            code="USER_SESSION_REQUIRED",
        )
    return ServicioAgente(db, contexto.empresa_id, contexto.usuario.id, modelo)


@router.post("/messages", response_model=AiReply)
def send_message(datos: AiMessageInput, contexto: ContextoActual, db: DbSession, modelo: Modelo):
    return _servicio(db, contexto, modelo).interpretar(datos.text)


@router.post("/actions/{id}/confirm", response_model=AiConfirmResult)
def confirm_action(
    id: ActionId,
    datos: AiConfirm,
    contexto: ContextoActual,
    db: DbSession,
    auditor: AuditorActual,
):
    accion, id_gasto = _servicio(db, contexto).confirmar(id, datos)
    estado = ESTADOS_API[accion.estado]
    corregido = estado == "corregido"
    instruccion = accion.instruccion_recibida[:200]
    auditor.registrar(
        "ia",
        "Corrigió y confirmó propuesta de IA" if corregido else "Confirmó propuesta de IA",
        f"Gasto #{id_gasto} registrado desde el agente. Instrucción: «{instruccion}»",
        entidad="gasto",
        id_entidad=id_gasto,
    )
    return AiConfirmResult(action_id=id, status=estado, expense_id=id_gasto)


@router.post("/actions/{id}/cancel", status_code=204)
def cancel_action(id: ActionId, contexto: ContextoActual, db: DbSession):
    _servicio(db, contexto).cancelar(id)


@router.get("/actions", response_model=Page[AiAction])
def list_actions(
    contexto: ContextoActual,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 50,
):
    return _servicio(db, contexto).historial(page=page, page_size=page_size)
