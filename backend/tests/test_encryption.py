import pytest, base64

from app.core.encryption import (
    EncryptionConfigurationError,
    EncryptionIntegrityError,
    decrypt_bytes,
    decrypt_text,
    encrypt_bytes,
    encrypt_text,
)


def test_encrypt_and_decrypt_text():
    original = "Clave de prueba del certificado SRI"

    ciphertext, nonce, tag = encrypt_text(original)

    assert ciphertext != original
    assert decrypt_text(ciphertext, nonce, tag) == original


def test_encrypt_and_decrypt_bytes():
    original = b"\x00IONDU\xff\x10"

    ciphertext, nonce, tag = encrypt_bytes(original)

    assert decrypt_bytes(ciphertext, nonce, tag) == original


def test_rejects_invalid_authentication_tag():
    ciphertext, nonce, tag = encrypt_text("Texto de prueba")
    invalid_tag = "dGFnX2ludmFsaWRv"

    assert tag != invalid_tag

    with pytest.raises(EncryptionIntegrityError):
        decrypt_text(ciphertext, nonce, invalid_tag)


def test_rejects_invalid_nonce():
    ciphertext, nonce, tag = encrypt_text("Texto de prueba")

    with pytest.raises(EncryptionIntegrityError):
        decrypt_text(ciphertext, "bnVsbw==", tag)


def test_missing_encryption_key(monkeypatch):
    monkeypatch.delenv("MASTER_ENCRYPTION_KEY", raising=False)

    from app.core import encryption

    monkeypatch.setattr(
        encryption,
        "get_settings",
        lambda: type(
            "SettingsWithoutKey",
            (),
            {"master_encryption_key": None},
        )(),
    )

    with pytest.raises(EncryptionConfigurationError):
        encryption.encrypt_text("Texto de prueba")

def test_rejects_modified_ciphertext():
    original = "Contraseña de prueba del certificado SRI"

    ciphertext, nonce, tag = encrypt_text(original)

    # Decodificamos el contenido cifrado para modificar un byte.
    ciphertext_bytes = bytearray(
        base64.b64decode(ciphertext)
    )

    # Alteramos un byte si el contenido no está vacío.
    assert ciphertext_bytes
    ciphertext_bytes[0] ^= 1

    # Volvemos a codificarlo en Base64.
    modified_ciphertext = base64.b64encode(
        bytes(ciphertext_bytes)
    ).decode("ascii")

    # La autenticación debe fallar al intentar descifrarlo.
    with pytest.raises(EncryptionIntegrityError):
        decrypt_text(modified_ciphertext, nonce, tag)
