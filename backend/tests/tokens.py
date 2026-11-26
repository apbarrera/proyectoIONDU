"""Tokens de prueba: se firman con una llave generada aquí, como lo hace el backend.

El verificador de prueba usa la llave pública de esa llave. Nada se conecta a la red.
"""

import time
import uuid

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

from app.core.seguridad import AUDIENCIA, EMISOR, VerificadorTokens

LLAVE_IONDU = ec.generate_private_key(ec.SECP256R1())
LLAVE_ATACANTE = ec.generate_private_key(ec.SECP256R1())


def crear_token(
    usuario: uuid.UUID, *, llave=LLAVE_IONDU, algoritmo: str = "ES256", **cambios
) -> str:
    """Token como los que emite el backend. Un cambio con valor None quita ese campo."""
    ahora = int(time.time())
    datos = {
        "sub": str(usuario),
        "email": "ana@empresa.ec",
        "aud": AUDIENCIA,
        "iss": EMISOR,
        "iat": ahora,
        "exp": ahora + 3600,
    } | cambios
    datos = {k: v for k, v in datos.items() if v is not None}
    return jwt.encode(datos, llave, algorithm=algoritmo)


def verificador_de_prueba() -> VerificadorTokens:
    return VerificadorTokens(EMISOR, lambda _token: LLAVE_IONDU.public_key())
