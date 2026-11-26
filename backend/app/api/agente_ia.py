"""Agente de IA (docs/API.md, sección 15). Cualquier usuario de la empresa lo usa."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Path, Query, UploadFile

from app.api.deps import AuditorActual, ContextoActual, DbSession, SoloAdministrador
from app.core.config import get_settings
from app.core.errors import ForbiddenError
from app.ia.cliente import ClienteOpenAICompatible, ModeloLenguaje
from app.ia.imagen import TAMANO_MAXIMO_BYTES, preparar_imagen
from app.ia.voz import TAMANO_MAXIMO_AUDIO, Transcriptor, TranscriptorOpenAICompatible
from app.schemas.agente_ia import (
    AiAction,
    AiConfirm,
    AiConfirmResult,
    AiMessageInput,
    AiReply,
    AiUsage,
    AiUsageLimitUpdate,
)
from app.schemas.common import Page
from app.services.agente_ia import ESTADOS_API, ServicioAgente
from app.services.consumo_ia import ConsumoIAService

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


def get_modelo_vision() -> ModeloLenguaje | None:
    """Cliente del modelo con visión (LLM_VISION_MODEL); None si no está configurado."""
    settings = get_settings()
    if not (settings.llm_base_url and settings.llm_vision_model):
        return None
    return ClienteOpenAICompatible(
        settings.llm_base_url,
        settings.llm_vision_model,
        settings.llm_api_key.get_secret_value() if settings.llm_api_key else None,
        settings.llm_timeout_seconds,
    )


Modelo = Annotated[ModeloLenguaje | None, Depends(get_modelo)]
ModeloVision = Annotated[ModeloLenguaje | None, Depends(get_modelo_vision)]


def get_transcriptor() -> Transcriptor | None:
    """Servicio de voz a texto (STT_*); None si no está configurado."""
    settings = get_settings()
    if not settings.stt_base_url:
        return None
    return TranscriptorOpenAICompatible(
        settings.stt_base_url,
        settings.stt_model,
        settings.stt_api_key.get_secret_value() if settings.stt_api_key else None,
        settings.llm_timeout_seconds,
    )


TranscriptorActual = Annotated[Transcriptor | None, Depends(get_transcriptor)]


def _servicio(db, contexto, modelo=None) -> ServicioAgente:
    # Las acciones del agente quedan a nombre de un usuario real.
    if contexto.usuario is None:
        raise ForbiddenError(
            "Para usar el agente de IA debes iniciar sesión con tu usuario.",
            code="USER_SESSION_REQUIRED",
        )
    return ServicioAgente(
        db,
        contexto.empresa_id,
        contexto.usuario.id,
        modelo,
        es_administrador=contexto.es_administrador,
    )


@router.post("/messages", response_model=AiReply)
def send_message(datos: AiMessageInput, contexto: ContextoActual, db: DbSession, modelo: Modelo):
    return _servicio(db, contexto, modelo).interpretar(datos.text)


@router.post("/images", response_model=AiReply)
def send_image(
    contexto: ContextoActual,
    db: DbSession,
    modelo: ModeloVision,
    image: Annotated[UploadFile, File(description="Foto de una factura, ticket o guía")],
    text: Annotated[str | None, Form(max_length=500)] = None,
):
    """Lee una foto (RF-6.3). La imagen se procesa en memoria y no se guarda."""
    try:
        # Se lee un byte de más para detectar un archivo demasiado grande sin cargarlo entero.
        contenido = image.file.read(TAMANO_MAXIMO_BYTES + 1)
    finally:
        image.file.close()
    servicio = _servicio(db, contexto, modelo)
    return servicio.interpretar_imagen(preparar_imagen(contenido), (text or "").strip() or None)


@router.post("/audio", response_model=AiReply)
def send_audio(
    contexto: ContextoActual,
    db: DbSession,
    modelo: Modelo,
    transcriptor: TranscriptorActual,
    audio: Annotated[UploadFile, File(description="Mensaje de voz (webm, ogg, mp4, wav o mp3)")],
):
    """Transcribe un mensaje de voz y lo interpreta (RF-6.4). El audio no se guarda."""
    try:
        contenido = audio.file.read(TAMANO_MAXIMO_AUDIO + 1)
    finally:
        audio.file.close()
    return _servicio(db, contexto, modelo).interpretar_voz(contenido, transcriptor)


@router.post("/actions/{id}/confirm", response_model=AiConfirmResult)
def confirm_action(
    id: ActionId,
    datos: AiConfirm,
    contexto: ContextoActual,
    db: DbSession,
    auditor: AuditorActual,
):
    accion, id_gasto, id_movimiento = _servicio(db, contexto).confirmar(id, datos)
    estado = ESTADOS_API[accion.estado]
    corregido = estado == "corregido"
    instruccion = accion.instruccion_recibida[:200]
    if id_gasto is not None:
        hecho, entidad, id_entidad = f"Gasto #{id_gasto}", "gasto", id_gasto
    else:
        hecho, entidad = f"Movimiento de inventario #{id_movimiento}", "movimiento_inventario"
        id_entidad = id_movimiento
    auditor.registrar(
        "ia",
        "Corrigió y confirmó propuesta de IA" if corregido else "Confirmó propuesta de IA",
        f"{hecho} registrado desde el agente. Instrucción: «{instruccion}»",
        entidad=entidad,
        id_entidad=id_entidad,
    )
    return AiConfirmResult(
        action_id=id, status=estado, expense_id=id_gasto, movement_id=id_movimiento
    )


@router.post("/actions/{id}/cancel", status_code=204)
def cancel_action(id: ActionId, contexto: ContextoActual, db: DbSession):
    _servicio(db, contexto).cancelar(id)


@router.get("/usage", response_model=AiUsage)
def get_usage(contexto: SoloAdministrador, db: DbSession):
    """Consumo de tokens del mes y de los últimos meses, con el límite (RF-6.14)."""
    return ConsumoIAService(db, contexto.empresa_id).resumen()


@router.put("/usage/limit", response_model=AiUsage)
def set_usage_limit(
    datos: AiUsageLimitUpdate, contexto: SoloAdministrador, db: DbSession, auditor: AuditorActual
):
    """Configura el tope mensual de tokens de la empresa; null lo quita (RNF-12)."""
    resumen = ConsumoIAService(db, contexto.empresa_id).configurar_limite(datos.monthly_limit)
    limite = (
        f"{datos.monthly_limit:,} tokens al mes".replace(",", ".")
        if datos.monthly_limit is not None
        else "sin límite"
    )
    auditor.registrar("ia", "Cambió el límite de tokens del agente", f"Nuevo límite: {limite}.")
    return resumen


@router.get("/actions", response_model=Page[AiAction])
def list_actions(
    contexto: ContextoActual,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 50,
):
    return _servicio(db, contexto).historial(page=page, page_size=page_size)
