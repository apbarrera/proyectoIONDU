"""Verificación de los tokens (JWT) que emite Supabase Auth.

El frontend inicia sesión contra Supabase y envía el token en cada petición
(`Authorization: Bearer <token>`). Aquí se comprueba que:
- la firma sea de Supabase (llave pública publicada en /auth/v1/.well-known/jwks.json);
- el algoritmo sea ES256 o RS256 (bloquea "alg: none" y la confusión con HS256);
- no esté vencido, sea de nuestro proyecto (iss) y de un usuario autenticado (aud);
- traiga el id del usuario (sub) como UUID.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import jwt

from app.core.errors import ServiceUnavailableError, UnauthenticatedError

ALGORITMOS_PERMITIDOS = ["ES256", "RS256"]  # llaves asimétricas de Supabase; nunca HS256 ni none
AUDIENCIA = "authenticated"
MARGEN_RELOJ_SEGUNDOS = 30


@dataclass(frozen=True)
class UsuarioAutenticado:
    id: UUID
    email: str | None


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

    @classmethod
    def para_supabase(cls, supabase_url: str) -> "VerificadorTokens":
        base = supabase_url.rstrip("/")
        # Descarga y guarda en memoria las llaves públicas (se renuevan cada 10 min).
        jwks = jwt.PyJWKClient(f"{base}/auth/v1/.well-known/jwks.json", lifespan=600, timeout=10)
        return cls(f"{base}/auth/v1", lambda token: jwks.get_signing_key_from_jwt(token).key)

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
        except jwt.PyJWKClientConnectionError as exc:
            raise ServiceUnavailableError(
                "No se pudo verificar la sesión. Intenta en un momento.", code="AUTH_UNAVAILABLE"
            ) from exc
        except jwt.ExpiredSignatureError as exc:
            raise UnauthenticatedError(
                "Tu sesión expiró. Inicia sesión de nuevo.", code="TOKEN_EXPIRED"
            ) from exc
        except jwt.PyJWTError as exc:
            raise UnauthenticatedError("Sesión inválida. Inicia sesión de nuevo.") from exc

        try:
            usuario_id = UUID(datos["sub"])
        except ValueError as exc:
            raise UnauthenticatedError("Sesión inválida. Inicia sesión de nuevo.") from exc
        return UsuarioAutenticado(id=usuario_id, email=datos.get("email"))
