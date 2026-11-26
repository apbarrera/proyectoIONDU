"""Tokens de acceso (JWT) del inicio de sesión propio.

El backend firma los tokens con su llave privada EC P-256 (ES256) al iniciar sesión
o renovarla, y en cada petición (`Authorization: Bearer <token>`) comprueba que:
- la firma corresponda a nuestra llave pública;
- el algoritmo sea ES256 (bloquea "alg: none" y la confusión con HS256);
- no esté vencido, lo haya emitido IONDU (iss) y sea para esta API (aud);
- traiga el id del usuario (sub) como UUID.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.core.errors import UnauthenticatedError

ALGORITMO = "ES256"
ALGORITMOS_PERMITIDOS = [ALGORITMO]  # nunca HS256 ni none
EMISOR = "iondu"
AUDIENCIA = "iondu-api"
MARGEN_RELOJ_SEGUNDOS = 30


@dataclass(frozen=True)
class UsuarioAutenticado:
    id: UUID
    email: str | None


def cargar_llave_privada(pem: str) -> ec.EllipticCurvePrivateKey:
    """Lee la llave PEM (acepta `\\n` escritos en una sola línea, como en .env)."""
    contenido = pem.strip().replace("\\n", "\n").encode()
    try:
        llave = serialization.load_pem_private_key(contenido, password=None)
    except (ValueError, TypeError) as exc:
        raise ValueError("AUTH_JWT_PRIVATE_KEY no es una llave privada PEM válida.") from exc
    if not isinstance(llave, ec.EllipticCurvePrivateKey) or not isinstance(
        llave.curve, ec.SECP256R1
    ):
        raise ValueError("AUTH_JWT_PRIVATE_KEY debe ser una llave EC P-256 (ES256).")
    return llave


class EmisorTokens:
    """Firma los tokens de acceso de corta duración."""

    def __init__(
        self,
        llave_privada: ec.EllipticCurvePrivateKey,
        *,
        duracion: timedelta,
        emisor: str = EMISOR,
        audiencia: str = AUDIENCIA,
    ):
        self._llave = llave_privada
        self._duracion = duracion
        self._emisor = emisor
        self._audiencia = audiencia

    @property
    def duracion_segundos(self) -> int:
        return int(self._duracion.total_seconds())

    def emitir(self, usuario_id: UUID, email: str, *, ahora: datetime | None = None) -> str:
        ahora = ahora or datetime.now(UTC)
        datos = {
            "sub": str(usuario_id),
            "email": email,
            "iss": self._emisor,
            "aud": self._audiencia,
            "iat": int(ahora.timestamp()),
            "exp": int((ahora + self._duracion).timestamp()),
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(datos, self._llave, algorithm=ALGORITMO)

    def verificador(self) -> "VerificadorTokens":
        publica = self._llave.public_key()
        return VerificadorTokens(self._emisor, lambda _token: publica, audiencia=self._audiencia)


class VerificadorTokens:
    def __init__(
        self,
        emisor: str,
        obtener_llave: Callable[[str], Any],
        *,
        audiencia: str = AUDIENCIA,
    ):
        """`obtener_llave(token)` devuelve la llave pública con que se firmó el token."""
        self._emisor = emisor
        self._obtener_llave = obtener_llave
        self._audiencia = audiencia

    def verificar(self, token: str) -> UsuarioAutenticado:
        try:
            llave = self._obtener_llave(token)
            datos = jwt.decode(
                token,
                llave,
                algorithms=ALGORITMOS_PERMITIDOS,
                audience=self._audiencia,
                issuer=self._emisor,
                leeway=MARGEN_RELOJ_SEGUNDOS,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise UnauthenticatedError(
                "Tu sesión expiró. Inicia sesión de nuevo.", code="TOKEN_EXPIRED"
            ) from exc
        except jwt.PyJWTError as exc:
            raise UnauthenticatedError("Sesión inválida. Inicia sesión de nuevo.") from exc

        try:
            usuario_id = UUID(datos["sub"])
        except (ValueError, TypeError, AttributeError) as exc:
            raise UnauthenticatedError("Sesión inválida. Inicia sesión de nuevo.") from exc
        return UsuarioAutenticado(id=usuario_id, email=datos.get("email"))
