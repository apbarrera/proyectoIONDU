"""Consumo y límite mensual de tokens del agente de IA (RF-6.1, RF-6.14, RNF-12).

- El mes es el calendario de Ecuador (America/Guayaquil).
- Cada llamada al modelo ya suma sus tokens en `consumo_tokens` (servicio del agente).
- Si la empresa tiene límite y el consumo del mes lo alcanzó, el agente no llama al
  modelo y responde 429. El tope se revisa ANTES de cada llamada: no se sabe cuánto
  consumirá la siguiente, así que el mes puede cerrar como mucho una llamada por encima.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import TIMEZONE
from app.core.errors import NotFoundError, TooManyRequestsError
from app.models import ConsumoTokens, Empresa
from app.schemas.agente_ia import AiUsage, AiUsageMonth

ZONA = ZoneInfo(TIMEZONE)
MESES_HISTORIAL = 6
AVISO_DESDE = 0.8  # desde el 80 % del límite el frontend avisa


def inicio_de_mes(ahora: datetime, meses_atras: int = 0) -> datetime:
    """Primer instante del mes (en Ecuador), `meses_atras` meses antes del actual."""
    local = ahora.astimezone(ZONA)
    indice = local.year * 12 + (local.month - 1) - meses_atras
    return datetime(indice // 12, indice % 12 + 1, 1, tzinfo=ZONA)


def limite_alcanzado_error() -> TooManyRequestsError:
    error = TooManyRequestsError(
        "Se alcanzó el límite mensual de tokens del agente de IA. "
        "El Administrador puede ampliarlo en Configuración → IA."
    )
    error.code = "AI_TOKEN_LIMIT_REACHED"
    return error


class ConsumoIAService:
    def __init__(self, db: Session, empresa_id: int, *, reloj=lambda: datetime.now(ZONA)):
        self.db = db
        self.empresa_id = empresa_id
        self._reloj = reloj

    def _empresa(self) -> Empresa:
        empresa = self.db.get(Empresa, self.empresa_id)
        if empresa is None:
            raise NotFoundError("No se encontró la empresa.")
        return empresa

    def _usado_desde(self, desde: datetime, hasta: datetime | None = None) -> int:
        condiciones = [ConsumoTokens.id_empresa == self.empresa_id, ConsumoTokens.fecha >= desde]
        if hasta is not None:
            condiciones.append(ConsumoTokens.fecha < hasta)
        total = self.db.scalar(
            select(
                func.coalesce(
                    func.sum(ConsumoTokens.tokens_prompt + ConsumoTokens.tokens_completado), 0
                )
            ).where(*condiciones)
        )
        return int(total or 0)

    def usado_en_el_mes(self) -> int:
        return self._usado_desde(inicio_de_mes(self._reloj()))

    def exigir_cupo(self) -> None:
        """Lanza 429 si la empresa tiene límite y ya lo alcanzó este mes."""
        limite = self._empresa().limite_tokens_ia_mensual
        if limite is not None and self.usado_en_el_mes() >= limite:
            raise limite_alcanzado_error()

    def resumen(self) -> AiUsage:
        ahora = self._reloj()
        limite = self._empresa().limite_tokens_ia_mensual
        historial = []
        for atras in range(MESES_HISTORIAL - 1, -1, -1):
            desde = inicio_de_mes(ahora, atras)
            hasta = inicio_de_mes(ahora, atras - 1) if atras else None
            historial.append(
                AiUsageMonth(month=f"{desde:%Y-%m}", used=self._usado_desde(desde, hasta))
            )
        usado = historial[-1].used
        if limite is None:
            porcentaje = None
        elif limite == 0:
            porcentaje = 100.0
        else:
            porcentaje = round(min(usado / limite, 1) * 100, 1)
        return AiUsage(
            monthly_limit=limite,
            used=usado,
            remaining=max(limite - usado, 0) if limite is not None else None,
            percent_used=porcentaje,
            near_limit=limite is not None and usado >= limite * AVISO_DESDE,
            limit_reached=limite is not None and usado >= limite,
            history=historial,
        )

    def configurar_limite(self, limite: int | None) -> AiUsage:
        self._empresa().limite_tokens_ia_mensual = limite
        self.db.commit()
        return self.resumen()
