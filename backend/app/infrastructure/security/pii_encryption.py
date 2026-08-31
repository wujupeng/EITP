"""PII 加密适配器 - 基于 PostgreSQL pgcrypto 对称加密。

加密存储邮箱/手机号/真实姓名，密钥由环境变量 EITP_PII_ENCRYPTION_KEY 管理。
"""

from __future__ import annotations

import os
import hashlib
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

logger = get_logger(__name__)


class PiiEncryptionAdapter:
    """PII 字段加密/解密适配器。

    使用 PostgreSQL pgcrypto 的 pgp_sym_encrypt/pgp_sym_decrypt 函数。
    密钥从环境变量 EITP_PII_ENCRYPTION_KEY 加载。
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._key = os.environ.get("EITP_PII_ENCRYPTION_KEY", "")
        if not self._key:
            logger.warning("pii_encryption_key_missing", msg="EITP_PII_ENCRYPTION_KEY not set, using fallback")
            self._key = "eitp-default-pii-key-change-in-production"

    async def encrypt(self, plaintext: Optional[str]) -> Optional[str]:
        if plaintext is None:
            return None
        result = await self._session.execute(
            text("SELECT pgp_sym_encrypt(:val, :key)"),
            {"val": plaintext, "key": self._key},
        )
        row = result.fetchone()
        if row is None:
            return None
        return row[0].hex() if hasattr(row[0], "hex") else str(row[0])

    async def decrypt(self, ciphertext: Optional[str]) -> Optional[str]:
        if ciphertext is None:
            return None
        result = await self._session.execute(
            text("SELECT pgp_sym_decrypt(:val::bytea, :key)"),
            {"val": ciphertext, "key": self._key},
        )
        row = result.fetchone()
        if row is None:
            return None
        return str(row[0])

    async def encrypt_batch(self, values: dict[str, Optional[str]]) -> dict[str, Optional[str]]:
        result: dict[str, Optional[str]] = {}
        for field_name, value in values.items():
            result[field_name] = await self.encrypt(value)
        return result

    async def decrypt_batch(self, values: dict[str, Optional[str]]) -> dict[str, Optional[str]]:
        result: dict[str, Optional[str]] = {}
        for field_name, value in values.items():
            result[field_name] = await self.decrypt(value)
        return result

    def hash_for_unique(self, plaintext: Optional[str]) -> Optional[str]:
        if plaintext is None:
            return None
        return hashlib.sha256(f"{self._key}:{plaintext}".encode()).hexdigest()