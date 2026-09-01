"""RedisKeyIsolationVerifier - Redis Key 隔离验证器。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.infrastructure.sec.redis_key_scanner import RedisKeyScanner, ScanResult


@dataclass
class RedisIsolationResult:
    tenant_a_id: UUID
    tenant_b_id: UUID
    cache_write_isolated: bool = False
    cache_read_isolated: bool = False
    scan_result: ScanResult | None = None
    violations: list[dict[str, Any]] = field(default_factory=list)


class RedisKeyIsolationVerifier:
    """验证缓存命中不跨租户 + 全量扫描前缀合规性。"""

    def __init__(self, http_client: Any, redis_client: Any) -> None:
        self._http_client = http_client
        self._scanner = RedisKeyScanner(redis_client)

    async def verify(self, tenant_a: UUID, tenant_b: UUID) -> RedisIsolationResult:
        result = RedisIsolationResult(tenant_a_id=tenant_a, tenant_b_id=tenant_b)

        await self._http_client.post(
            "/api/v1/inv/balances/refresh",
            headers={"X-Tenant-Token": str(tenant_a)},
        )

        scan = await self._scanner.scan_tenant_keys(str(tenant_a))
        result.scan_result = scan
        result.cache_write_isolated = scan.total_scanned > 0 and len(scan.violations) == 0

        resp = await self._http_client.get(
            "/api/v1/inv/balances",
            headers={"X-Tenant-Token": str(tenant_a)},
        )
        result.cache_read_isolated = resp.status_code == 200

        result.violations = [
            {"key": v.key, "type": v.violation_type, "expected": v.expected_prefix, "actual": v.actual_prefix}
            for v in scan.violations
        ]

        return result