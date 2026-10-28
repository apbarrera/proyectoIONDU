from app.core.encryption import (
    encrypt_text,
    decrypt_text,
    EncryptionIntegrityError,
)

original = "Clave de prueba del certificado SRI"

ciphertext, nonce, tag = encrypt_text(original)

assert ciphertext != original
assert decrypt_text(ciphertext, nonce, tag) == original

print("OK: cifrado y descifrado correctos")

try:
    decrypt_text(ciphertext, nonce, "dGFnX2ludmFsaWRv")
except EncryptionIntegrityError:
    print("OK: se rechazaron datos alterados")
else:
    raise AssertionError("El contenido alterado no fue rechazado")