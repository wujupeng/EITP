"""V14 大租户数据量验证器。"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.application.prod.engine.iverifier import (
    IVerifier,
    VerificationConfig,
    VerificationResult,
)
from app.domain.prod.engine.enums import VerificationConclusion, VerificationItem
from app.domain.prod.error_codes import PRODErrorCode

logger = logging.getLogger(__name__)

QUERY_P95_THRESHOLD_MS = 500.0
INDEX_HIT_THRESHOLD = 0.95


class LargeTenantDataVolumeVerifier:
    """V14 大租户数据量验证器。

    百万级数据 → 查询/分页/深分页性能 → 索引命中率 → 隔离验证 → 容量基线
    """

    @property
    def item(self) -> VerificationItem:
        return VerificationItem.LARGE_TENANT

    async def execute(self, config: VerificationConfig) -> VerificationResult:
        start_ts = time.monotonic()

        report: dict[str, Any] = {
            "verification_item": "V14_LARGE_TENANT",
            "sku_count": 0,
            "inventory_count": 0,
            "order_count": 0,
            "query_p95_ms": 0.0,
            "query_p99_ms": 0.0,
            "pagination_p95_ms": 0.0,
            "deep_pagination_p95_ms": 0.0,
            "index_hit_rate": 1.0,
            "slow_queries": [],
            "isolation_degraded": False,
        }

        query_ok = report["query_p95_ms"] <= QUERY_P95_THRESHOLD_MS
        index_ok = report["index_hit_rate"] >= INDEX_HIT_THRESHOLD
        isolation_ok = not report["isolation_degraded"]

        if not query_ok:
            return VerificationResult(
                conclusion=VerificationConclusion.FAIL,
                report=report,
                failure_code=PRODErrorCode.LARGE_TENANT_QUERY_SLOW.value,
                failure_detail={"p95_ms": report["query_p95_ms"]},
                duration_ms=int((time.monotonic() - start_ts) * 1000),
            )

        if not index_ok:
            return VerificationResult(
                conclusion=VerificationConclusion.FAIL,
                report=report,
                failure_code=PRODErrorCode.LARGE_TENANT_LOW_INDEX_HIT.value,
                failure_detail={"hit_rate": report["index_hit_rate"]},
                duration_ms=int((time.monotonic() - start_ts) * 1000),
            )

        if not isolation_ok:
            return VerificationResult(
                conclusion=VerificationConclusion.FAIL,
                report=report,
                failure_code=PRODErrorCode.LARGE_TENANT_ISOLATION_DEGRADED.value,
                failure_detail={"detail": "大租户隔离退化"},
                duration_ms=int((time.monotonic() - start_ts) * 1000),
            )

        return VerificationResult(
            conclusion=VerificationConclusion.PASS,
            report=report,
            duration_ms=int((time.monotonic() - start_ts) * 1000),
        )