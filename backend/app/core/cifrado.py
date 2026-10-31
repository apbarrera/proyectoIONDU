"""Cifrado de secretos guardados en la base (certificados .p12, sus claves, credenciales IMAP).

AES-256-GCM con la llave maestra MASTER_ENCRYPTION_KEY (32 bytes en base64), que vive
solo como variable de entorno. Ver docs/DECISIONES.md, 2.5.

Formato de lo guardado:  [versión 1 byte][nonce 12 bytes][cifrado + etiqueta 16 bytes]

- Cada cifrado usa un nonce aleatorio nuevo (reusarlo con la misma llave rompe GCM).
- El "contexto" (p. ej. "empresa:7:p12") se amarra al dato: un valor copiado a otra
  empresa o a otro campo no se descifra.
- GCM detecta cualquier alteración del dato guardado.

Generar una llave nueva:  python -m app.core.cifrado
"""

import base64
import binascii
import os
from functools import lru_cache

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings

VERSION = b"\x01"
_LARGO_NONCE = 12
_LARGO_LLAVE = 32  # AES-256


class DatoCifradoInvalidoError(Exception):
    """El dato no se pudo descifrar: llave o contexto incorrectos, o fue alterado."""


class Cifrador:
    def __init__(self, llave: bytes):
        if len(llave) != _LARGO_LLAVE:
            raise ValueError(f"La llave maestra debe tener {_LARGO_LLAVE} bytes.")
        self._aes = AESGCM(llave)

    def cifrar(self, datos: bytes, contexto: str) -> bytes:
        nonce = os.urandom(_LARGO_NONCE)
        return VERSION + nonce + self._aes.encrypt(nonce, datos, contexto.encode("utf-8"))

    def descifrar(self, cifrado: bytes, contexto: str) -> bytes:
        if not cifrado.startswith(VERSION) or len(cifrado) < 1 + _LARGO_NONCE + 16:
            raise DatoCifradoInvalidoError("Formato o versión de cifrado desconocidos.")
        nonce = cifrado[1 : 1 + _LARGO_NONCE]
        try:
            return self._aes.decrypt(nonce, cifrado[1 + _LARGO_NONCE :], contexto.encode("utf-8"))
        except InvalidTag as exc:
            raise DatoCifradoInvalidoError(
                "No se pudo descifrar: llave o contexto incorrectos, o el dato fue alterado."
            ) from exc


def generar_llave_maestra() -> str:
    """Llave nueva de 32 bytes en base64, para MASTER_ENCRYPTION_KEY."""
    return base64.b64encode(os.urandom(_LARGO_LLAVE)).decode("ascii")


def leer_llave_maestra(valor: str) -> bytes:
    try:
        llave = base64.b64decode(valor, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("MASTER_ENCRYPTION_KEY no es base64 válido.") from exc
    if len(llave) != _LARGO_LLAVE:
        raise ValueError(f"MASTER_ENCRYPTION_KEY debe tener {_LARGO_LLAVE} bytes en base64.")
    return llave


@lru_cache
def _cifrador(valor: str) -> Cifrador:
    return Cifrador(leer_llave_maestra(valor))


def get_cifrador() -> Cifrador:
    secreto = get_settings().master_encryption_key

    if secreto is None:
        raise RuntimeError(
            "Falta MASTER_ENCRYPTION_KEY (genera una con: python -m app.core.cifrado)."
        )

    valor = secreto.get_secret_value()

    if not valor:
        raise RuntimeError(
            "Falta MASTER_ENCRYPTION_KEY (genera una con: python -m app.core.cifrado)."
        )

    return _cifrador(valor)


if __name__ == "__main__":
    print(generar_llave_maestra())
