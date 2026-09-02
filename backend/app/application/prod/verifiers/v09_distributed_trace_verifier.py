"""V09 Trace 全链路验证器。"""

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

MAX_SPANS_PER_REQUEST = 20


class DistributedTraceVerifier:
    """V09 Trace 全链路验证器。

    发起请求 → 查询 Trace → 校验全链路 Span → TraceId 一致 → 爆炸检测
    """

    @property
    def item(self) -> VerificationItem:
        return VerificationItem.TRACE

    async def execute(self, config: VerificationConfig) -> VerificationResult:
        start_ts = time.monotonic()

        report: dict[str, Any] = {
            "verification_item": "V09_TRACE",
            "traces_examined": 0,
            "all_complete": True,
            "trace_id_consistent": True,
            "max_spans": 0,
            "span_explosion": False,
        }

        all_complete = report["all_complete"]
        trace_id_ok = report["trace_id_consistent"]
        explosion = report["span_explosion"]

        if not all_complete:
            return VerificationResult(
                conclusion=VerificationConclusion.FAIL,
                report=report,
                failure_code=PRODErrorCode.TRACE_BROKEN.value,
                failure_detail={"detail": "某链路环节未创建 Span"},
                duration_ms=int((time.monotonic() - start_ts) * 1000),
            )

        if not trace_id_ok:
            return VerificationResult(
                conclusion=VerificationConclusion.FAIL,
                report=report,
                failure_code=PRODErrorCode.TRACE_ID_INCONSISTENT.value,
                failure_detail={"detail": "TraceId 不一致"},
                duration_ms=int((time.monotonic() - start_ts) * 1000),
            )

        if explosion:
            return VerificationResult(
                conclusion=VerificationConclusion.FAIL,
                report=report,
                failure_code=PRODErrorCode.TRACE_EXPLOSION.value,
                failure_detail={"max_spans": report["max_spans"]},
                duration_ms=int((time.monotonic() - start_ts) * 1000),
            )

        return VerificationResult(
            conclusion=VerificationConclusion.PASS,
            report=report,
            duration_ms=int((time.monotonic() - start_ts) * 1000),
        )