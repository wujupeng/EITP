"""RedisKeyScanner - SCAN 分批游标扫描 Redis Key 前缀合规性。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.interfaces.middleware.error_handler import SECError, SECErrorCode

_SCAN_COUNT = 1000
_SCAN_TIMEOUT_MS = 60000
_EXPECTED_PREFIX_TEMPLATE = "eitp:{tenant_id}:"
_PLATFORM_WHITELIST = ("platform:config:", "platform:mdm:group_product:")


@dataclass
class KeyViolation:
    key: str
    violation_type: str
    expected_prefix: str
    actual_prefix: str = ""


@dataclass
class ScanResult:
    total_scanned: int = 0
    violations: list[KeyViolation] = field(default_factory=list)
    duration_ms: float = 0.0


class RedisKeyScanner:
    """使用 SCAN（非 KEYS）分批扫描，不阻塞 Redis 主线程。"""

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client

    async def scan_tenant_keys(self, tenant_id: str) -> ScanResult:
        import time
        start = time.monotonic()
        expected_prefix = _EXPECTED_PREFIX_TEMPLATE.format(tenant_id=tenant_id)
        result = ScanResult()
        cursor = 0

        while True:
            cursor, keys = await self._redis.scan(cursor=cursor, count=_SCAN_COUNT, match="*")
            result.total_scanned += len(keys)
            for key in keys:
                key_str = key if isinstance(key, str) else key.decode("utf-8")
                violation = self._check_key(key_str, tenant_id, expected_prefix)
                if violation:
                    result.violations.append(violation)
            if cursor == 0:
                break
            elapsed = (time.monotonic() - start) * 1000
            if elapsed > _SCAN_TIMEOUT_MS:
                raise SECError(SECErrorCode.REDIS_SCAN_TIMEOUT, f"Scan exceeded {_SCAN_TIMEOUT_MS}ms")

        result.duration_ms = (time.monotonic() - start) * 1000
        return result

    def _check_key(self, key: str, tenant_id: str, expected_prefix: str) -> KeyViolation | None:
        for wl in _PLATFORM_WHITELIST:
            if key.startswith(wl):
                return None
        if key.startswith(expected_prefix):
            return None
        if ":" in key:
            parts = key.split(":", 2)
            if len(parts) >= 2 and parts[1] != tenant_id:
                return KeyViolation(
                    key=key,
                    violation_type="CROSS_TENANT_PREFIX",
                    expected_prefix=expected_prefix,
                    actual_prefix=parts[0] + ":" + parts[1] + ":",
                )
        return KeyViolation(
            key=key,
            violation_type="MISSING_TENANT_PREFIX",
            expected_prefix=expected_prefix,
            actual_prefix="",
        )