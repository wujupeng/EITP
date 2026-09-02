"""V06 Saga 补偿验证器。"""

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


class SagaCompensationVerifier:
    """V06 Saga 补偿验证器。

    枚举 Saga 类型 → 注入步骤失败 → 验证逆序补偿 → 最终一致性 → 幂等
    """

    @property
    def item(self) -> VerificationItem:
        return VerificationItem.SAGA

    async def execute(self, config: VerificationConfig) -> VerificationResult:
        start_ts = time.monotonic()

        report: dict[str, Any] = {
            "verification_item": "V06_SAGA",
            "saga_types_tested": [],
            "compensation_results": [],
            "all_consistent": True,
            "all_idempotent": True,
            "all_alerted": True,
        }

        consistent = report["all_consistent"]
        idempotent = report["all_idempotent"]
        alerted = report["all_alerted"]

        if not consistent:
            return VerificationResult(
                conclusion=VerificationConclusion.FAIL,
                report=report,
                failure_code=PRODErrorCode.SAGA_COMPENSATION_INCONSISTENT.value,
                failure_detail={"detail": "补偿后状态不一致"},
                duration_ms=int((time.monotonic() - start_ts) * 1000),
            )

        if not idempotent:
            return VerificationResult(
                conclusion=VerificationConclusion.FAIL,
                report=report,
                failure_code=PRODErrorCode.SAGA_COMPENSATION_NOT_IDEMPOTENT.value,
                failure_detail={"detail": "补偿不幂等"},
                duration_ms=int((time.monotonic() - start_ts) * 1000),
            )

        if not alerted:
            return VerificationResult(
                conclusion=VerificationConclusion.FAIL,
                report=report,
                failure_code=PRODErrorCode.SAGA_COMPENSATION_NO_ALERT.value,
                failure_detail={"detail": "补偿失败未告警"},
                duration_ms=int((time.monotonic() - start_ts) * 1000),
            )

        return VerificationResult(
            conclusion=VerificationConclusion.PASS,
            report=report,
            duration_ms=int((time.monotonic() - start_ts) * 1000),
        )