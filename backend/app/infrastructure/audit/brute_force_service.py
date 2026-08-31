"""暴力破解防护服务 - 账号+IP 双维度 Redis 计数器。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.infrastructure.cache.redis_client import get_redis


class BruteForceService:
    """暴力破解防护 - 双维度（账号+IP）计数与锁定封禁。

    规则：
    - 账号维度：5 次/15min 锁定、10 次/1h 告警
    - IP 维度：20 次/60min 封禁
    """

    ACCOUNT_PREFIX = "iam:bf:account:"
    IP_PREFIX = "iam:bf:ip:"
    ACCOUNT_LOCK_PREFIX = "iam:bf:lock:account:"
    IP_BAN_PREFIX = "iam:bf:ban:ip:"

    def __init__(
        self,
        max_attempts: int = 5,
        lockout_minutes: int = 15,
        ip_ban_threshold: int = 20,
        ip_ban_minutes: int = 60,
    ) -> None:
        self._max_attempts = max_attempts
        self._lockout_minutes = lockout_minutes
        self._ip_ban_threshold = ip_ban_threshold
        self._ip_ban_minutes = ip_ban_minutes

    async def record_failure(self, account: str, ip: str) -> tuple[bool, bool]:
        """记录失败尝试，返回 (account_locked, ip_banned)。"""
        r = await get_redis()

        acct_key = f"{self.ACCOUNT_PREFIX}{account}"
        ip_key = f"{self.IP_PREFIX}{ip}"

        acct_count = await r.incr(acct_key)
        await r.expire(acct_key, self._lockout_minutes * 60)
        ip_count = await r.incr(ip_key)
        await r.expire(ip_key, self._ip_ban_minutes * 60)

        account_locked = False
        ip_banned = False

        if acct_count >= self._max_attempts:
            lock_key = f"{self.ACCOUNT_LOCK_PREFIX}{account}"
            await r.setex(lock_key, self._lockout_minutes * 60, "1")
            account_locked = True

        if ip_count >= self._ip_ban_threshold:
            ban_key = f"{self.IP_BAN_PREFIX}{ip}"
            await r.setex(ban_key, self._ip_ban_minutes * 60, "1")
            ip_banned = True

        return account_locked, ip_banned

    async def is_account_locked(self, account: str) -> bool:
        r = await get_redis()
        lock_key = f"{self.ACCOUNT_LOCK_PREFIX}{account}"
        return bool(await r.exists(lock_key))

    async def is_ip_banned(self, ip: str) -> bool:
        r = await get_redis()
        ban_key = f"{self.IP_BAN_PREFIX}{ip}"
        return bool(await r.exists(ban_key))

    async def reset_account(self, account: str) -> None:
        r = await get_redis()
        await r.delete(f"{self.ACCOUNT_PREFIX}{account}")
        await r.delete(f"{self.ACCOUNT_LOCK_PREFIX}{account}")