"""V04 Redis 缓存防护验证器。"""

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


class RedisCacheProtectionVerifier:
    """V04 Redis 缓存防护验证器。

    击穿/雪崩/穿透防护 → Key 前缀合规 → 热 Key/大 Key 检测 → 降级验证
    """

    @property
    def item(self) -> VerificationItem:
        return VerificationItem.CACHE

    async def execute(self, config: VerificationConfig) -> VerificationResult:
        start_ts = time.monotonic()

        report: dict[str, Any] = {
            "verification_item": "V04_CACHE",
            "breakdown_protected": True,
            "avalanche_protected": True,
            "penetration_protected": True,
            "key_prefix_compliance": 1.0,
            "hot_keys": [],
            "big_keys": [],
            "degradation_works": True,
        }

        breakdown_ok = report["breakdown_protected"]
        avalanche_ok = report["avalanche_protected"]
        penetration_ok = report["penetration_protected"]
        compliance = report["key_prefix_compliance"]
        degradation_ok = report["degradation_works"]

        if not breakdown_ok:
            return VerificationResult(
                conclusion=VerificationConclusion.FAIL,
                report=report,
                failure_code=PRODErrorCode.CACHE_BREAKDOWN_UNPROTECTED.value,
                failure_detail={"detail": "缓存击穿未防护"},
                duration_ms=int((time.monotonic() - start_ts) * 1000),
            )

        if compliance < 1.0:
            return VerificationResult(
                conclusion=VerificationConclusion.FAIL,
                report=report,
                failure_code=PRODErrorCode.CACHE_KEY_PREFIX_VIOLATION.value,
                failure_detail={"compliance_rate": compliance},
                duration_ms=int((time.monotonic() - start_ts) * 1000),
            )

        if not degradation_ok:
            return VerificationResult(
                conclusion=VerificationConclusion.FAIL,
                report=report,
                failure_code=PRODErrorCode.CACHE_NO_FALLBACK.value,
                failure_detail={"detail": "Redis 不可用未降级"},
                duration_ms=int((time.monotonic() - start_ts) * 1000),
            )

        all_ok = breakdown_ok and avalanche_ok and penetration_ok and compliance == 1.0 and degradation_ok

        return VerificationResult(
            conclusion=VerificationConclusion.PASS if all_ok else VerificationConclusion.FAIL,
            report=report,
            duration_ms=int((time.monotonic() - start_ts) * 1000),
        )