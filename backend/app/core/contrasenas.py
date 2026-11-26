"""Hash de contraseñas con argon2id (parámetros por defecto de argon2-cffi, RFC 9106)."""

from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

LONGITUD_MINIMA = 10
LONGITUD_MAXIMA = 128

_hasher = PasswordHasher()


def hashear(contrasena: str) -> str:
    return _hasher.hash(contrasena)


def verificar(hash_guardado: str, contrasena: str) -> bool:
    """False si no coincide o si la cuenta no tiene una contraseña utilizable ("!")."""
    try:
        return _hasher.verify(hash_guardado, contrasena)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def necesita_rehash(hash_guardado: str) -> bool:
    return _hasher.check_needs_rehash(hash_guardado)


@lru_cache
def _hash_ficticio() -> str:
    return _hasher.hash("contrasena-ficticia-para-igualar-tiempos")


def simular_verificacion(contrasena: str) -> None:
    """Gasta el mismo tiempo que una verificación real cuando el correo no existe,
    para que la respuesta no delate qué correos están registrados."""
    verificar(_hash_ficticio(), contrasena)


def validar_nueva(contrasena: str) -> None:
    if not LONGITUD_MINIMA <= len(contrasena) <= LONGITUD_MAXIMA:
        raise ValueError(
            f"La contraseña debe tener entre {LONGITUD_MINIMA} y {LONGITUD_MAXIMA} caracteres."
        )
