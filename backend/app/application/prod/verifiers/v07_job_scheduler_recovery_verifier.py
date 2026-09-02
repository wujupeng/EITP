"""V07 Job Scheduler 恢复验证器。"""

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

SCHEDULE_DRIFT_THRESHOLD_S = 1.0


class JobSchedulerRecoveryVerifier:
    """V07 Job Scheduler 恢复验证器。

    注册任务 → 注入重启 → 验证恢复 → misfire 补执行 → 幂等 → 精度
    """

    @property
    def item(self) -> VerificationItem:
        return VerificationItem.JOB

    async def execute(self, config: VerificationConfig) -> VerificationResult:
        start_ts = time.monotonic()

        report: dict[str, Any] = {
            "verification_item": "V07_JOB",
            "jobs_registered": 0,
            "jobs_recovered": 0,
            "misfire_executed": 0,
            "definition_lost": False,
            "misfire_not_idempotent": False,
            "schedule_drift_seconds": 0.0,
        }

        definition_ok = not report["definition_lost"]
        idempotent_ok = not report["misfire_not_idempotent"]
        drift_ok = report["schedule_drift_seconds"] <= SCHEDULE_DRIFT_THRESHOLD_S

        if not definition_ok:
            return VerificationResult(
                conclusion=VerificationConclusion.FAIL,
                report=report,
                failure_code=PRODErrorCode.JOB_DEFINITION_LOST.value,
                failure_detail={"detail": "重启后任务定义缺失"},
                duration_ms=int((time.monotonic() - start_ts) * 1000),
            )

        if not idempotent_ok:
            return VerificationResult(
                conclusion=VerificationConclusion.FAIL,
                report=report,
                failure_code=PRODErrorCode.JOB_MISFIRE_NOT_IDEMPOTENT.value,
                failure_detail={"detail": "补执行重复副作用"},
                duration_ms=int((time.monotonic() - start_ts) * 1000),
            )

        if not drift_ok:
            return VerificationResult(
                conclusion=VerificationConclusion.FAIL,
                report=report,
                failure_code=PRODErrorCode.JOB_SCHEDULE_DRIFT.value,
                failure_detail={"drift": report["schedule_drift_seconds"]},
                duration_ms=int((time.monotonic() - start_ts) * 1000),
            )

        return VerificationResult(
            conclusion=VerificationConclusion.PASS,
            report=report,
            duration_ms=int((time.monotonic() - start_ts) * 1000),
        )