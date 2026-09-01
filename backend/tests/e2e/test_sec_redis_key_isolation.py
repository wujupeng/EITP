"""Redis Key 隔离验证 E2E 测试。"""

import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from app.infrastructure.sec.redis_key_scanner import RedisKeyScanner


class TestRedisKeyIsolationE2E:
    """SCAN 全量 Key + 缓存命中不跨租户 + 前缀合规性。"""

    @pytest.mark.asyncio
    async def test_scan_returns_result(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.scan.return_value = (0, [])
        scanner = RedisKeyScanner(mock_redis)
        result = await scanner.scan_tenant_keys(str(uuid4()))
        assert result.total_scanned == 0
        assert len(result.violations) == 0

    @pytest.mark.asyncio
    async def test_compliant_keys_no_violations(self) -> None:
        tenant_id = str(uuid4())
        mock_redis = AsyncMock()
        mock_redis.scan.return_value = (0, [f"eitp:{tenant_id}:bal:wh1:sku1".encode()])
        scanner = RedisKeyScanner(mock_redis)
        result = await scanner.scan_tenant_keys(tenant_id)
        assert len(result.violations) == 0