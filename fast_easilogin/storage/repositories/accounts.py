from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from fast_easilogin.storage.encryption.base import CredentialEncryptor, EncryptedValue
from fast_easilogin.storage.models import UserCredentialTable


async def rotate_credentials(db: AsyncSession, old_encryptor: CredentialEncryptor, new_encryptor: CredentialEncryptor) -> int:
    rows = (await db.execute(select(UserCredentialTable))).scalars().all()
    replacements = []
    for row in rows:
        account = old_encryptor.decrypt(EncryptedValue(row.account_ciphertext, row.account_nonce, row.encryption_algorithm, row.encryption_key_version))
        password = old_encryptor.decrypt(EncryptedValue(row.password_ciphertext, row.password_nonce, row.encryption_algorithm, row.encryption_key_version))
        account_value = new_encryptor.encrypt(account)
        password_value = new_encryptor.encrypt(password)
        replacements.append((row, account_value, password_value))
    for row, account_value, password_value in replacements:
        row.account_ciphertext = account_value.ciphertext
        row.account_nonce = account_value.nonce
        row.password_ciphertext = password_value.ciphertext
        row.password_nonce = password_value.nonce
        row.encryption_algorithm = new_encryptor.algorithm
        row.encryption_key_version = new_encryptor.key_version
    return len(replacements)


@dataclass(frozen=True, slots=True)
class DecryptedCredentials:
    account: str
    password: str


async def save_credentials(
    db: AsyncSession,
    user_id: str,
    account: str,
    password: str,
    encryptor: CredentialEncryptor,
) -> None:
    account_value = encryptor.encrypt(account)
    password_value = encryptor.encrypt(password)
    row = await db.get(UserCredentialTable, user_id)
    if row is None:
        row = UserCredentialTable(
            user_id=user_id,
            account_ciphertext=b"",
            account_nonce=b"",
            password_ciphertext=b"",
            password_nonce=b"",
            encryption_algorithm=encryptor.algorithm,
            encryption_key_version=encryptor.key_version,
        )
        db.add(row)
    row.account_ciphertext = account_value.ciphertext
    row.account_nonce = account_value.nonce
    row.password_ciphertext = password_value.ciphertext
    row.password_nonce = password_value.nonce
    row.encryption_algorithm = encryptor.algorithm
    row.encryption_key_version = encryptor.key_version


async def load_credentials(db: AsyncSession, user_id: str, encryptor: CredentialEncryptor) -> DecryptedCredentials | None:
    row = await db.get(UserCredentialTable, user_id)
    if row is None:
        return None
    account = encryptor.decrypt(EncryptedValue(row.account_ciphertext, row.account_nonce, row.encryption_algorithm, row.encryption_key_version))
    password = encryptor.decrypt(EncryptedValue(row.password_ciphertext, row.password_nonce, row.encryption_algorithm, row.encryption_key_version))
    return DecryptedCredentials(account=account, password=password)


async def delete_credentials(db: AsyncSession, user_id: str) -> None:
    row = await db.get(UserCredentialTable, user_id)
    if row is not None:
        await db.delete(row)
