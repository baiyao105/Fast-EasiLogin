from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fast_easilogin.dashboard.v1.models import UpstreamUserProfile
from fast_easilogin.storage.encryption.base import CredentialEncryptor, EncryptedValue
from fast_easilogin.storage.models import UserRecord
from fast_easilogin.storage.repositories.accounts import save_credentials
from fast_easilogin.storage.store import delete_user, get_user, save_user, set_user_active


@dataclass(slots=True)
class Verification:
    token: str
    session_id: str
    account: EncryptedValue
    password: EncryptedValue
    profile: UpstreamUserProfile
    expires_at: datetime
    used: bool = False


class AccountApplication:
    def __init__(self) -> None:
        self.verifications: dict[str, Verification] = {}

    def issue(self, session_id: str, account: str, password: str, profile: UpstreamUserProfile, encryptor: CredentialEncryptor) -> Verification:
        value = Verification(secrets.token_urlsafe(32), session_id, encryptor.encrypt(account), encryptor.encrypt(password), profile, datetime.now(UTC) + timedelta(minutes=5))
        self.verifications[value.token] = value
        return value

    async def create(self, db, session_id: str, token: str, encryptor: CredentialEncryptor | None):
        value = self.verifications.get(token)
        if value is None or value.used or value.session_id != session_id or value.expires_at <= datetime.now(UTC):
            raise ValueError("invalid_verification_token")
        if encryptor is None:
            raise RuntimeError("credential_encryption_unavailable")
        if await get_user(db, value.profile.user_id):
            raise ValueError("account_already_exists")
        record = UserRecord(user_id=value.profile.user_id, phone=value.profile.phone, password="", nick_name=value.profile.nickname, real_name=value.profile.real_name, avatar_url=value.profile.avatar_url)
        await save_user(db, record)
        await save_credentials(db, record.user_id, encryptor.decrypt(value.account), encryptor.decrypt(value.password), encryptor)
        value.used = True
        return record

    async def set_active(self, db, user_id: str, active: bool) -> bool:
        return await set_user_active(db, user_id, active)

    async def delete(self, db, user_id: str) -> bool:
        return await delete_user(db, user_id)
