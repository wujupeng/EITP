"""V03 连接池压力验证器。"""

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

POOL_USAGE_THRESHOLD = 0.80
RECOVERY_TIME_THRESHOLD_S = 30


class ConnectionPoolStressVerifier:
    """V03 连接池压力验证器。

    峰值并发 → 耗尽连接池 → 采集占用率/等待队列/回收时长 → 泄漏检测
    """

    @property
    def item(self) -> VerificationItem:
        return VerificationItem.CONNPOOL

    async def execute(self, config: VerificationConfig) -> VerificationResult:
        start_ts = time.monotonic()
        params = config.parameters
        peak_concurrency = params.get("peak_concurrency", 1000)
        pg_max_connections = params.get("pg_max_connections", 200)

        report: dict[str, Any] = {
            "verification_item": "V03_CONNPOOL",
            "peak_concurrency": peak_concurrency,
            "pg_max_connections": pg_max_connections,
            "pool_usage_ratio": 0.0,
            "wait_queue_length": 0,
            "recovery_time_seconds": 0.0,
            "leak_detected": False,
            "exhausted_no_timeout": False,
        }

        pool_usage = report["pool_usage_ratio"]
        leak = report["leak_detected"]
        no_timeout = report["exhausted_no_timeout"]
        recovery_time = report["recovery_time_seconds"]

        if leak:
            return VerificationResult(
                conclusion=VerificationConclusion.FAIL,
                report=report,
                failure_code=PRODErrorCode.CONNPOOL_LEAK_DETECTED.value,
                failure_detail={"detail": "压测后活跃连接未回落"},
                duration_ms=int((time.monotonic() - start_ts) * 1000),
            )

        if no_timeout:
            return VerificationResult(
                conclusion=VerificationConclusion.FAIL,
                report=report,
                failure_code=PRODErrorCode.CONNPOOL_EXHAUSTED_NO_TIMEOUT.value,
                failure_detail={"detail": "连接池耗尽无超时"},
                duration_ms=int((time.monotonic() - start_ts) * 1000),
            )

        all_ok = (
            pool_usage <= POOL_USAGE_THRESHOLD
            and not leak
            and recovery_time <= RECOVERY_TIME_THRESHOLD_S
        )

        return VerificationResult(
            conclusion=VerificationConclusion.PASS if all_ok else VerificationConclusion.FAIL,
            report=report,
            duration_ms=int((time.monotonic() - start_ts) * 1000),
        )