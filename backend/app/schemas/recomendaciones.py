"""Recomendaciones generadas con IA (RF-7). Solo informativas."""

from datetime import datetime
from typing import Literal

from app.schemas.common import ApiModel


class AiRecommendation(ApiModel):
    title: str
    description: str
    category: Literal["Ventas", "Gastos", "Finanzas", "Inventario"]
    priority: Literal["alta", "media", "baja"]
    data_used: list[str]  # qué datos usó (RF-7.4)


class AiAnalysis(ApiModel):
    analysis: str  # explicación sencilla de cómo va el negocio (RF-7.1)
    recommendations: list[AiRecommendation]
    generated_at: datetime
    model: str
