"""Recomendaciones del negocio con IA (RF-7). Solo el Administrador, como el dashboard."""

from fastapi import APIRouter

from app.api.agente_ia import Modelo
from app.api.deps import AuditorActual, DbSession, SoloAdministrador
from app.schemas.recomendaciones import AiAnalysis
from app.services.recomendaciones_ia import RecomendacionesIAService

router = APIRouter(tags=["Recomendaciones"])


@router.post("/recommendations/ai", response_model=AiAnalysis)
def generate_ai_recommendations(
    contexto: SoloAdministrador, db: DbSession, modelo: Modelo, auditor: AuditorActual
):
    """Genera el análisis del mes con IA. Gasta tokens: el frontend lo pide a demanda."""
    analisis = RecomendacionesIAService(db, contexto.empresa_id, modelo).generar()
    auditor.registrar(
        "ia",
        "Generó recomendaciones con IA",
        f"{len(analisis.recommendations)} recomendaciones con {analisis.model}.",
    )
    return analisis
