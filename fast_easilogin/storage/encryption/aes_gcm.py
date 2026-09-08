from __future__ import annotations

import base64
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from fast_easilogin.storage.encryption.base import EncryptedValue

AES_KEY_BYTES = 32


class AesGcmEncryptor:
    algorithm = "aes-256-gcm"

    def __init__(self, key: bytes, key_version: int = 1) -> None:
        if len(key) != AES_KEY_BYTES:
            raise ValueError("AES-256-GCM key must contain exactly 32 bytes")  # noqa: TRY003
        self._key = key
        self._key_version = key_version

    @property
    def key_version(self) -> int:
        return self._key_version

    def encrypt(self, plaintext: str) -> EncryptedValue:
        nonce = secrets.token_bytes(12)
        ciphertext = AESGCM(self._key).encrypt(nonce, plaintext.encode("utf-8"), None)
        return EncryptedValue(ciphertext, nonce, self.algorithm, self._key_version)

    def decrypt(self, value: EncryptedValue) -> str:
        plaintext = AESGCM(self._key).decrypt(value.nonce, value.ciphertext, None)
        return plaintext.decode("utf-8")


def decode_environment_key(value: str) -> bytes:
    try:
        key = base64.urlsafe_b64decode(value.encode("ascii"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("FAST_EASILOGIN_ENCRYPTION_KEY must be URL-safe base64") from exc  # noqa: TRY003
    if len(key) != AES_KEY_BYTES:
        raise ValueError("FAST_EASILOGIN_ENCRYPTION_KEY must decode to 32 bytes")  # noqa: TRY003
    return key
