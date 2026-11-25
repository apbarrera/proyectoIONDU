"""Un "Supabase falso" para las pruebas: firma tokens con una llave generada aquí.

El backend los verifica con la llave pública, igual que haría con las que publica
Supabase. Nada se conecta a la red.
"""

import time
import uuid

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

from app.core.seguridad import VerificadorTokens

EMISOR = "https://proyecto-prueba.supabase.co/auth/v1"
LLAVE_SUPABASE = ec.generate_private_key(ec.SECP256R1())
LLAVE_ATACANTE = ec.generate_private_key(ec.SECP256R1())


def crear_token(
    usuario: uuid.UUID, *, llave=LLAVE_SUPABASE, algoritmo: str = "ES256", **cambios
) -> str:
    """Token como los de Supabase. Un cambio con valor None quita ese campo."""
    ahora = int(time.time())
    datos = {
        "sub": str(usuario),
        "email": "ana@empresa.ec",
        "aud": "authenticated",
        "role": "authenticated",
        "iss": EMISOR,
        "iat": ahora,
        "exp": ahora + 3600,
    } | cambios
    datos = {k: v for k, v in datos.items() if v is not None}
    return jwt.encode(datos, llave, algorithm=algoritmo)


def verificador_de_prueba() -> VerificadorTokens:
    return VerificadorTokens(EMISOR, lambda _token: LLAVE_SUPABASE.public_key())
