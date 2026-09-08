from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EncryptedValue:
    ciphertext: bytes
    nonce: bytes
    algorithm: str
    key_version: int


class CredentialEncryptor(Protocol):
    @property
    def algorithm(self) -> str: ...

    @property
    def key_version(self) -> int: ...

    def encrypt(self, plaintext: str) -> EncryptedValue: ...

    def decrypt(self, value: EncryptedValue) -> str: ...
