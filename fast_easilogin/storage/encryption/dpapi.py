from __future__ import annotations

import sys


class DpapiKeyProvider:
    """Protects an AES master key with the current Windows user context."""

    def protect(self, key: bytes) -> bytes:
        if sys.platform != "win32":
            raise RuntimeError("Windows DPAPI is only available on Windows")  # noqa: TRY003
        import win32crypt  # noqa: PLC0415

        return win32crypt.CryptProtectData(key, "fast_easilogin", None, None, None, 0)[1]

    def unprotect(self, protected_key: bytes) -> bytes:
        if sys.platform != "win32":
            raise RuntimeError("Windows DPAPI is only available on Windows")  # noqa: TRY003
        import win32crypt  # noqa: PLC0415

        return win32crypt.CryptUnprotectData(protected_key, None, None, None, 0)[1]
