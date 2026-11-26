"""Preparación de las fotos que se envían al modelo de visión (RF-6.3).

La imagen se procesa solo en memoria y no se guarda (los contenedores no tienen estado).
Se valida que sea de verdad una foto y se reduce: una foto de celular a tamaño completo
consume miles de tokens y no mejora la lectura de un ticket.
"""

import base64
import io
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.errors import UnprocessableError

TAMANO_MAXIMO_BYTES = 8 * 1024 * 1024
FORMATOS = {"JPEG", "PNG", "WEBP"}
LADO_MAXIMO = 1280
# Tope de píxeles antes de decodificar: evita "bombas" de descompresión.
PIXELES_MAXIMOS = 50_000_000


def _invalida() -> UnprocessableError:
    return UnprocessableError(
        "El archivo no es una imagen válida. Sube una foto JPG, PNG o WEBP.",
        code="INVALID_IMAGE",
    )


def preparar_imagen(contenido: bytes) -> str:
    """Devuelve la imagen como data URL JPEG, lista para el modelo."""
    if not contenido:
        raise _invalida()
    if len(contenido) > TAMANO_MAXIMO_BYTES:
        raise UnprocessableError("La imagen pesa más de 8 MB.", code="IMAGE_TOO_LARGE")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            imagen = Image.open(io.BytesIO(contenido))
            if imagen.format not in FORMATOS:
                raise _invalida()
            ancho, alto = imagen.size
            if ancho * alto > PIXELES_MAXIMOS:
                raise _invalida()
            imagen.load()
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise _invalida() from None

    # Respeta la orientación de la cámara y descarta los metadatos (EXIF, GPS).
    imagen = ImageOps.exif_transpose(imagen).convert("RGB")
    imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
    salida = io.BytesIO()
    imagen.save(salida, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(salida.getvalue()).decode("ascii")
