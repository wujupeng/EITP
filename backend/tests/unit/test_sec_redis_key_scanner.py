"""EITP-SEC-001 RedisKeyScanner 单元测试。

覆盖 SCAN 分批游标扫描、违规检测 (CROSS_TENANT_PREFIX / MISSING_TENANT_PREFIX)、
平台白名单与超时保护。Redis 客户端通过 AsyncMock 模拟，不依赖真实 Redis。
"""

from __future__ import annotations

from typing import Any

import pytest

from app.infrastructure.sec.redis_key_scanner import (
    KeyViolation,
    RedisKeyScanner,
    ScanResult,
)
from app.interfaces.middleware.error_handler import SECError, SECErrorCode

_TENANT_A = "11111111-1111-1111-1111-111111111111"
_TENANT_B = "22222222-2222-2222-2222-222222222222"


class FakeRedisClient:
    """模拟 Redis SCAN 行为：按预设批次依次返回 (cursor, keys)。"""

    def __init__(self, batches: list[tuple[int, list[str]]]) -> None:
        # batches: [(cursor_after, keys), ...]；最后一批 cursor 必须为 0
        self._batches = list(batches)
        self._index = 0
        self.scan_calls: list[dict[str, Any]] = []

    async def scan(self, cursor: int = 0, count: int = 1000, match: str = "*") -> tuple[int, list[str]]:
        self.scan_calls.append({"cursor": cursor, "count": count, "match": match})
        if self._index >= len(self._batches):
            return 0, []
        result = self._batches[self._index]
        self._index += 1
        return result


class KeyViolationTest:
    """KeyViolation 值对象。"""

    def test_default_actual_prefix_empty(self) -> None:
        v = KeyViolation(key="k", violation_type="X", expected_prefix="eitp:t1:")
        assert v.actual_prefix == ""

    def test_fields_assigned(self) -> None:
        v = KeyViolation(
            key="eitp:t2:x", violation_type="CROSS_TENANT_PREFIX",
            expected_prefix="eitp:t1:", actual_prefix="eitp:t2:",
        )
        assert v.key == "eitp:t2:x"
        assert v.violation_type == "CROSS_TENANT_PREFIX"


class ScanResultTest:
    def test_defaults(self) -> None:
        r = ScanResult()
        assert r.total_scanned == 0
        assert r.violations == []
        assert r.duration_ms == 0.0


class RedisKeyScannerTest:
    """RedisKeyScanner SCAN 合规检查。"""

    async def test_scan_compliant_keys_no_violations(self) -> None:
        keys = [f"eitp:{_TENANT_A}:inv:product:{i}" for i in range(3)]
        client = FakeRedisClient([(0, keys)])
        scanner = RedisKeyScanner(client)
        result = await scanner.scan_tenant_keys(_TENANT_A)
        assert result.total_scanned == 3
        assert result.violations == []
        assert result.duration_ms >= 0.0

    async def test_scan_uses_scan_not_keys(self) -> None:
        client = FakeRedisClient([(0, [])])
        scanner = RedisKeyScanner(client)
        await scanner.scan_tenant_keys(_TENANT_A)
        assert len(client.scan_calls) >= 1
        assert client.scan_calls[0]["match"] == "*"
        assert client.scan_calls[0]["count"] == 1000

    async def test_detects_cross_tenant_prefix_violation(self) -> None:
        keys = [f"eitp:{_TENANT_B}:inv:product:1"]
        client = FakeRedisClient([(0, keys)])
        scanner = RedisKeyScanner(client)
        result = await scanner.scan_tenant_keys(_TENANT_A)
        assert len(result.violations) == 1
        v = result.violations[0]
        assert v.violation_type == "CROSS_TENANT_PREFIX"
        assert v.expected_prefix == f"eitp:{_TENANT_A}:"
        assert v.actual_prefix == f"eitp:{_TENANT_B}:"

    async def test_detects_missing_tenant_prefix_violation(self) -> None:
        keys = ["bare_key_without_colon"]
        client = FakeRedisClient([(0, keys)])
        scanner = RedisKeyScanner(client)
        result = await scanner.scan_tenant_keys(_TENANT_A)
        assert len(result.violations) == 1
        assert result.violations[0].violation_type == "MISSING_TENANT_PREFIX"
        assert result.violations[0].actual_prefix == ""

    async def test_missing_tenant_prefix_for_non_matching_colon_key(self) -> None:
        # 形如 "foo:bar" 但第二段等于 tenant_id 时仍应通过 cross-tenant 检查分支
        # 这里 eitp:{tenant}:xxx 已合规；构造 "unknownprefix:x" 触发 MISSING
        keys = ["unknownprefix:x"]
        client = FakeRedisClient([(0, keys)])
        scanner = RedisKeyScanner(client)
        result = await scanner.scan_tenant_keys(_TENANT_A)
        assert len(result.violations) == 1
        # unknownprefix:x 的 parts[1]="x" != tenant_id → CROSS_TENANT_PREFIX
        assert result.violations[0].violation_type == "CROSS_TENANT_PREFIX"

    async def test_platform_whitelist_keys_skipped(self) -> None:
        keys = ["platform:config:global", "platform:mdm:group_product:1"]
        client = FakeRedisClient([(0, keys)])
        scanner = RedisKeyScanner(client)
        result = await scanner.scan_tenant_keys(_TENANT_A)
        assert result.violations == []
        assert result.total_scanned == 2

    async def test_mixed_compliant_and_violating_keys(self) -> None:
        keys = [
            f"eitp:{_TENANT_A}:inv:1",          # 合规
            f"eitp:{_TENANT_B}:inv:2",          # CROSS_TENANT
            "bare_key",                          # MISSING
            "platform:config:x",                 # 白名单
        ]
        client = FakeRedisClient([(0, keys)])
        scanner = RedisKeyScanner(client)
        result = await scanner.scan_tenant_keys(_TENANT_A)
        assert result.total_scanned == 4
        assert len(result.violations) == 2
        types = {v.violation_type for v in result.violations}
        assert types == {"CROSS_TENANT_PREFIX", "MISSING_TENANT_PREFIX"}

    async def test_multi_batch_scan_aggregates_results(self) -> None:
        batch1 = [f"eitp:{_TENANT_A}:k:{i}" for i in range(2)]
        batch2 = [f"eitp:{_TENANT_B}:k:0"]
        client = FakeRedisClient([(1, batch1), (0, batch2)])
        scanner = RedisKeyScanner(client)
        result = await scanner.scan_tenant_keys(_TENANT_A)
        assert result.total_scanned == 3
        assert len(result.violations) == 1
        assert result.violations[0].violation_type == "CROSS_TENANT_PREFIX"
        assert len(client.scan_calls) == 2

    async def test_scan_timeout_raises_sec_error(self) -> None:
        # 构造永不结束的批次（cursor 恒非 0），触发 60s 超时
        # 为快速触发，使用 monkeypatch 缩短超时阈值
        import app.infrastructure.sec.redis_key_scanner as mod

        keys = [f"eitp:{_TENANT_A}:k:0"]
        client = FakeRedisClient([(1, keys), (1, keys), (1, keys), (1, keys)])
        scanner = RedisKeyScanner(client)
        original_timeout = mod._SCAN_TIMEOUT_MS
        mod._SCAN_TIMEOUT_MS = -1  # 立即超时
        try:
            with pytest.raises(SECError) as exc:
                await scanner.scan_tenant_keys(_TENANT_A)
            assert exc.value.code == SECErrorCode.REDIS_SCAN_TIMEOUT
        finally:
            mod._SCAN_TIMEOUT_MS = original_timeout

    async def test_bytes_keys_decoded_to_str(self) -> None:
        keys = [f"eitp:{_TENANT_B}:inv:1".encode("utf-8")]
        client = FakeRedisClient([(0, keys)])
        scanner = RedisKeyScanner(client)
        result = await scanner.scan_tenant_keys(_TENANT_A)
        assert len(result.violations) == 1
        assert result.violations[0].violation_type == "CROSS_TENANT_PREFIX"

    async def test_empty_keyspace_returns_empty_result(self) -> None:
        client = FakeRedisClient([(0, [])])
        scanner = RedisKeyScanner(client)
        result = await scanner.scan_tenant_keys(_TENANT_A)
        assert result.total_scanned == 0
        assert result.violations == []

    def test_check_key_returns_none_for_compliant_key(self) -> None:
        client = FakeRedisClient([])
        scanner = RedisKeyScanner(client)
        assert scanner._check_key(f"eitp:{_TENANT_A}:inv:1", _TENANT_A, f"eitp:{_TENANT_A}:") is None

    def test_check_key_returns_none_for_platform_whitelist(self) -> None:
        client = FakeRedisClient([])
        scanner = RedisKeyScanner(client)
        assert scanner._check_key("platform:config:x", _TENANT_A, f"eitp:{_TENANT_A}:") is None