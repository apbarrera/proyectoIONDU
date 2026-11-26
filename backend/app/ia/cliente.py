"""Cliente de modelos de lenguaje con la API de OpenAI (`/v1/chat/completions`).

Sirve igual para Ollama en local y para OpenAI u otro proveedor compatible en
producción: solo cambian LLM_BASE_URL, LLM_MODEL y LLM_API_KEY.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.core.errors import ServiceUnavailableError

logger = logging.getLogger("iondu.ia")
MAX_TOKENS_RESPUESTA = 800
INTENTOS = 2


@dataclass(frozen=True)
class RespuestaModelo:
    datos: dict[str, Any]
    modelo: str
    tokens_prompt: int
    tokens_completado: int


class ModeloLenguaje(Protocol):
    def completar_json(
        self, mensajes: list[dict[str, Any]], esquema: dict[str, Any]
    ) -> RespuestaModelo: ...


def _no_disponible() -> ServiceUnavailableError:
    return ServiceUnavailableError(
        "El agente de IA no está disponible en este momento. Intenta de nuevo en un rato.",
        code="AI_UNAVAILABLE",
    )


class ClienteOpenAICompatible:
    def __init__(self, base_url: str, modelo: str, api_key: str | None, timeout: float):
        self.base_url = base_url.rstrip("/")
        self.modelo = modelo
        self.api_key = api_key
        self.timeout = timeout

    def completar_json(
        self, mensajes: list[dict[str, Any]], esquema: dict[str, Any]
    ) -> RespuestaModelo:
        """Pide una respuesta que cumpla `esquema` (salida estructurada) y la devuelve."""
        cuerpo = {
            "model": self.modelo,
            "messages": mensajes,
            "temperature": 0,
            # Tope de seguridad: con salida estructurada, un modelo pequeño puede quedarse
            # generando espacios sin fin.
            "max_tokens": MAX_TOKENS_RESPUESTA,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "respuesta_agente", "schema": esquema, "strict": True},
            },
        }
        encabezados = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        # Un modelo pequeño a veces corta el JSON (p. ej., si llega al tope de tokens):
        # se reintenta una vez antes de rendirse.
        for intento in range(1, INTENTOS + 1):
            try:
                respuesta = httpx.post(
                    f"{self.base_url}/chat/completions",
                    json=cuerpo,
                    headers=encabezados,
                    timeout=self.timeout,
                )
                respuesta.raise_for_status()
                datos = respuesta.json()
            except httpx.HTTPError as exc:
                logger.error("El modelo no respondió: %s", type(exc).__name__)
                raise _no_disponible() from None
            except ValueError:
                logger.error("El servicio del modelo respondió algo que no es JSON.")
                raise _no_disponible() from None
            try:
                eleccion = datos["choices"][0]
                resultado = json.loads(eleccion["message"]["content"])
                if isinstance(resultado, dict):
                    break
            except (KeyError, IndexError, TypeError, ValueError):
                pass
            elecciones = datos.get("choices") if isinstance(datos, dict) else None
            fin = (elecciones or [{}])[0].get("finish_reason")
            logger.warning(
                "Respuesta del modelo con formato inválido (intento %s, fin: %s).", intento, fin
            )
        else:
            raise _no_disponible()

        if not isinstance(resultado, dict):
            raise _no_disponible()
        uso = datos.get("usage") or {}
        return RespuestaModelo(
            datos=resultado,
            modelo=str(datos.get("model") or self.modelo)[:50],
            tokens_prompt=int(uso.get("prompt_tokens") or 0),
            tokens_completado=int(uso.get("completion_tokens") or 0),
        )
