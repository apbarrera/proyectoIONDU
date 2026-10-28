
import base64
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings


NONCE_BYTES = 12
KEY_BYTES = 32


class EncryptionConfigurationError(RuntimeError):
    """La clave maestra de cifrado no está configurada correctamente."""


class EncryptionIntegrityError(RuntimeError):
    """No se pudo autenticar el contenido cifrado."""


def _get_key() -> bytes:
    settings = get_settings()
    secret = settings.master_encryption_key

    if secret is None:
        raise EncryptionConfigurationError(
            "Falta configurar MASTER_ENCRYPTION_KEY."
        )

    try:
        key = base64.b64decode(
            secret.get_secret_value(),
            validate=True,
        )
    except (ValueError, TypeError) as exc:
        raise EncryptionConfigurationError(
            "MASTER_ENCRYPTION_KEY debe ser una clave Base64 válida."
        ) from exc

    if len(key) != KEY_BYTES:
        raise EncryptionConfigurationError(
            "MASTER_ENCRYPTION_KEY debe representar exactamente "
            "32 bytes para AES-256-GCM."
        )

    return key


def encrypt_bytes(plaintext: bytes) -> tuple[str, str, str]:
    """Cifra bytes y devuelve (ciphertext, nonce, tag), codificados en Base64."""
    if not isinstance(plaintext, bytes):
        raise TypeError("plaintext debe ser bytes.")

    nonce = os.urandom(NONCE_BYTES)
    encrypted_with_tag = AESGCM(_get_key()).encrypt(
        nonce,
        plaintext,
        None,
    )

    ciphertext = encrypted_with_tag[:-16]
    tag = encrypted_with_tag[-16:]

    return (
        base64.b64encode(ciphertext).decode("ascii"),
        base64.b64encode(nonce).decode("ascii"),
        base64.b64encode(tag).decode("ascii"),
    )


def decrypt_bytes(
    ciphertext_b64: str,
    nonce_b64: str,
    tag_b64: str,
) -> bytes:
    """Descifra y autentica bytes previamente cifrados por encrypt_bytes."""
    try:
        ciphertext = base64.b64decode(ciphertext_b64, validate=True)
        nonce = base64.b64decode(nonce_b64, validate=True)
        tag = base64.b64decode(tag_b64, validate=True)
    except (ValueError, TypeError) as exc:
        raise EncryptionIntegrityError(
            "El contenido cifrado tiene un formato inválido."
        ) from exc

    if len(nonce) != NONCE_BYTES or len(tag) != 16:
        raise EncryptionIntegrityError(
            "El nonce o la etiqueta de autenticación tienen una longitud inválida."
        )

    try:
        return AESGCM(_get_key()).decrypt(
            nonce,
            ciphertext + tag,
            None,
        )
    except InvalidTag as exc:
        raise EncryptionIntegrityError(
            "Falló la autenticación del contenido cifrado. "
            "Verifica la clave y los datos almacenados."
        ) from exc


def encrypt_text(plaintext: str) -> tuple[str, str, str]:
    """Cifra texto UTF-8 y devuelve (ciphertext, nonce, tag) en Base64."""
    if not isinstance(plaintext, str):
        raise TypeError("plaintext debe ser str.")

    return encrypt_bytes(plaintext.encode("utf-8"))


def decrypt_text(
    ciphertext_b64: str,
    nonce_b64: str,
    tag_b64: str,
) -> str:
    """Descifra texto UTF-8 previamente cifrado por encrypt_text."""
    try:
        return decrypt_bytes(
            ciphertext_b64,
            nonce_b64,
            tag_b64,
        ).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EncryptionIntegrityError(
            "El contenido descifrado no es texto UTF-8 válido."
        ) from exc
