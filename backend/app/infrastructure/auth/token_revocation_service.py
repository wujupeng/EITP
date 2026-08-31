"""Token 撤销服务 - Redis jti 撤销列表。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.infrastructure.cache.redis_client import get_redis


class TokenRevocationService:
    """Token 撤销服务 - 基于 Redis jti 撤销列表。

    撤销列表 TTL = Token 剩余时效，传播延迟 ≤30s。
    """

    REVOCATION_PREFIX = "iam:revoked:jti:"
    USER_REVOCATION_PREFIX = "iam:revoked:user:"

    async def revoke_token(self, jti: str, user_id: str, reason: str, expires_at: datetime) -> None:
        r = await get_redis()
        now = datetime.now(timezone.utc)
        ttl = int((expires_at - now).total_seconds())
        if ttl <= 0:
            return
        key = f"{self.REVOCATION_PREFIX}{jti}"
        await r.setex(key, ttl, reason)

    async def is_revoked(self, jti: str) -> bool:
        r = await get_redis()
        key = f"{self.REVOCATION_PREFIX}{jti}"
        result = await r.exists(key)
        return bool(result)

    async def revoke_all_user_tokens(self, user_id: str, ttl_seconds: int = 1800) -> None:
        """撤销用户所有 Token - 停用/注销/强制下线时调用。"""
        r = await get_redis()
        key = f"{self.USER_REVOCATION_PREFIX}{user_id}"
        await r.setex(key, ttl_seconds, "revoked")

    async def is_user_revoked(self, user_id: str) -> bool:
        r = await get_redis()
        key = f"{self.USER_REVOCATION_PREFIX}{user_id}"
        result = await r.exists(key)
        return bool(result)


_revocation_service: Optional[TokenRevocationService] = None


def get_revocation_service() -> TokenRevocationService:
    global _revocation_service
    if _revocation_service is None:
        _revocation_service = TokenRevocationService()
    return _revocation_service