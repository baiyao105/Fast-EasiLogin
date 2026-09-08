from __future__ import annotations

import base64
import os

from fast_easilogin.storage.encryption.aes_gcm import AesGcmEncryptor, decode_environment_key
from fast_easilogin.storage.encryption.base import CredentialEncryptor
from fast_easilogin.storage.encryption.dpapi import DpapiKeyProvider


def create_encryptor(key_source: str = "environment", key_version: int = 1) -> CredentialEncryptor:
    if key_source == "environment":
        source = os.environ.get("FAST_EASILOGIN_ENCRYPTION_KEY")
        if not source:
            raise RuntimeError("FAST_EASILOGIN_ENCRYPTION_KEY is required")  # noqa: TRY003
        return AesGcmEncryptor(decode_environment_key(source), key_version)
    if key_source == "dpapi":
        protected = os.environ.get("FAST_EASILOGIN_DPAPI_KEY")
        if not protected:
            raise RuntimeError("FAST_EASILOGIN_DPAPI_KEY is required for dpapi")  # noqa: TRY003
        try:
            key = DpapiKeyProvider().unprotect(base64.urlsafe_b64decode(protected))
        except (ValueError, UnicodeError) as exc:
            raise ValueError("FAST_EASILOGIN_DPAPI_KEY must be URL-safe base64") from exc  # noqa: TRY003
        return AesGcmEncryptor(key, key_version)
    raise ValueError(f"Unsupported encryption key source: {key_source}")  # noqa: TRY003
