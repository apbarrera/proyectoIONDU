"""Entrada por voz (RF-6.4): el audio se convierte en texto y sigue el camino del texto.

La transcripción usa la API de OpenAI (`/v1/audio/transcriptions`): en local, un servidor
de Whisper (speaches) en Docker; en producción, el proveedor que se configure en STT_*.
El audio se procesa en memoria y no se guarda.
"""

import logging
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.errors import ServiceUnavailableError, UnprocessableError

logger = logging.getLogger("iondu.ia")

TAMANO_MAXIMO_AUDIO = 5 * 1024 * 1024  # ~5 min de voz en Opus; el navegador corta al minuto
TEXTO_MAXIMO = 2000  # igual que un mensaje escrito
TIPOS_MIME = {
    "webm": "audio/webm",
    "ogg": "audio/ogg",
    "mp4": "audio/mp4",
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
}


@dataclass(frozen=True)
class Transcripcion:
    texto: str
    modelo: str


class Transcriptor(Protocol):
    def transcribir(self, audio: bytes, formato: str) -> Transcripcion: ...


def detectar_formato(audio: bytes) -> str:
    """Formato real del audio por sus primeros bytes (no por el nombre ni el Content-Type)."""
    if len(audio) > TAMANO_MAXIMO_AUDIO:
        raise UnprocessableError("El audio pesa más de 5 MB.", code="AUDIO_TOO_LARGE")
    cabecera = audio[:12]
    if cabecera.startswith(b"\x1a\x45\xdf\xa3"):  # Matroska/WebM (Chrome, Firefox)
        formato = "webm"
    elif cabecera.startswith(b"OggS"):
        formato = "ogg"
    elif cabecera[4:8] == b"ftyp":  # MP4/M4A (Safari)
        formato = "mp4"
    elif cabecera.startswith(b"RIFF") and cabecera[8:12] == b"WAVE":
        formato = "wav"
    elif cabecera.startswith(b"ID3") or cabecera[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        formato = "mp3"
    else:
        formato = None
    # Menos de 1 KB no alcanza para una palabra: es un archivo vacío o cortado.
    if formato is None or len(audio) < 1024:
        raise UnprocessableError(
            "El archivo no es un audio válido. Graba el mensaje de nuevo.", code="INVALID_AUDIO"
        )
    return formato


def _no_disponible() -> ServiceUnavailableError:
    return ServiceUnavailableError(
        "La transcripción de voz no está disponible en este momento. Escribe el mensaje.",
        code="AI_UNAVAILABLE",
    )


class TranscriptorOpenAICompatible:
    def __init__(self, base_url: str, modelo: str, api_key: str | None, timeout: float):
        self.base_url = base_url.rstrip("/")
        self.modelo = modelo
        self.api_key = api_key
        self.timeout = timeout

    def transcribir(self, audio: bytes, formato: str) -> Transcripcion:
        encabezados = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        try:
            respuesta = httpx.post(
                f"{self.base_url}/audio/transcriptions",
                files={"file": (f"mensaje.{formato}", audio, TIPOS_MIME[formato])},
                data={"model": self.modelo, "language": "es", "response_format": "json"},
                headers=encabezados,
                timeout=self.timeout,
            )
            respuesta.raise_for_status()
            texto = respuesta.json()["text"]
        except httpx.HTTPError as exc:
            logger.error("La transcripción falló: %s", type(exc).__name__)
            raise _no_disponible() from None
        except (ValueError, KeyError, TypeError):
            logger.error("El servicio de transcripción respondió algo inesperado.")
            raise _no_disponible() from None
        if not isinstance(texto, str):
            raise _no_disponible()
        return Transcripcion(" ".join(texto.split())[:TEXTO_MAXIMO], self.modelo[:50])
