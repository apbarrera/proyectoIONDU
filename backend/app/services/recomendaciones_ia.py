"""Análisis y recomendaciones del negocio con IA (RF-7.1 a RF-7.4).

Toma el dashboard de este mes y del anterior (calculado por el backend), se lo envía al
modelo y valida la respuesta. No guarda nada ni cambia datos (RF-7.3); solo suma los
tokens del pedido y respeta el límite mensual de la empresa (RNF-12).
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import TIMEZONE
from app.core.errors import ServiceUnavailableError
from app.ia.cliente import ModeloLenguaje
from app.ia.recomendaciones import (
    datos_del_negocio,
    esquema,
    interpretar,
    mensaje_usuario,
    prompt_sistema,
)
from app.models import ConsumoTokens
from app.schemas.recomendaciones import AiAnalysis, AiRecommendation
from app.services.consumo_ia import ConsumoIAService
from app.services.dashboard import DashboardService

ZONA = ZoneInfo(TIMEZONE)


class RecomendacionesIAService:
    def __init__(
        self,
        db: Session,
        empresa_id: int,
        modelo: ModeloLenguaje | None,
        *,
        reloj=lambda: datetime.now(ZONA),
    ):
        self.db = db
        self.empresa_id = empresa_id
        self.modelo = modelo
        self._reloj = reloj

    def generar(self) -> AiAnalysis:
        if self.modelo is None:
            raise ServiceUnavailableError(
                "El agente de IA no está configurado en este servidor.", code="AI_NOT_CONFIGURED"
            )
        ConsumoIAService(self.db, self.empresa_id).exigir_cupo()

        hoy = self._reloj().astimezone(ZONA).date()
        inicio = hoy.replace(day=1)
        fin_anterior = inicio - timedelta(days=1)
        dashboard = DashboardService(self.db, self.empresa_id)
        actual = dashboard.resumen(inicio, hoy)
        anterior = dashboard.resumen(fin_anterior.replace(day=1), fin_anterior)

        respuesta = self.modelo.completar_json(
            [
                {"role": "system", "content": prompt_sistema()},
                {"role": "user", "content": mensaje_usuario(datos_del_negocio(actual, anterior))},
            ],
            esquema(),
        )
        self.db.add(
            ConsumoTokens(
                id_empresa=self.empresa_id,
                modelo_ia=respuesta.modelo,
                tokens_prompt=respuesta.tokens_prompt,
                tokens_completado=respuesta.tokens_completado,
            )
        )
        self.db.commit()

        analisis = interpretar(respuesta.datos)
        return AiAnalysis(
            analysis=analisis.resumen,
            recommendations=[
                AiRecommendation(
                    title=r.titulo,
                    description=r.descripcion,
                    category=r.categoria,
                    priority=r.prioridad,
                    data_used=r.datos_utilizados,
                )
                for r in analisis.recomendaciones
            ],
            generated_at=self._reloj(),
            model=respuesta.modelo,
        )
