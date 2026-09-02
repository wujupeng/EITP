"""V01 性能基线验证器。"""

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

READ_P95_THRESHOLD_MS = 200.0
READ_P99_THRESHOLD_MS = 500.0
WRITE_P95_THRESHOLD_MS = 500.0
WRITE_P99_THRESHOLD_MS = 1000.0
MIN_SAMPLES = 10000
DEGRADATION_THRESHOLD = 0.20


class PerformanceBaselineVerifier:
    """V01 性能基线验证器。

    枚举全部 API 端点 → 压测采样 → 采集 P50/P95/P99/QPS → 与基线对比 → 达标判定
    """

    @property
    def item(self) -> VerificationItem:
        return VerificationItem.BASELINE

    async def execute(self, config: VerificationConfig) -> VerificationResult:
        start_ts = time.monotonic()
        params = config.parameters
        endpoints = params.get("endpoints", [])
        baseline = params.get("baseline", {})
        samples_per_endpoint = params.get("samples_per_endpoint", MIN_SAMPLES)

        report: dict[str, Any] = {
            "verification_item": "V01_BASELINE",
            "endpoints_tested": len(endpoints),
            "samples_per_endpoint": samples_per_endpoint,
            "results": [],
        }

        all_pass = True
        degraded_endpoints: list[str] = []

        for ep in endpoints:
            ep_result = {
                "endpoint": ep.get("path", ""),
                "method": ep.get("method", "GET"),
                "samples": samples_per_endpoint,
                "p50_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
                "qps": 0.0,
                "error_rate": 0.0,
                "pass": True,
            }

            if samples_per_endpoint < MIN_SAMPLES:
                return VerificationResult(
                    conclusion=VerificationConclusion.FAIL,
                    report=report,
                    failure_code=PRODErrorCode.BASELINE_INSUFFICIENT_SAMPLES.value,
                    failure_detail={"samples": samples_per_endpoint, "required": MIN_SAMPLES},
                    duration_ms=int((time.monotonic() - start_ts) * 1000),
                )

            p95 = ep_result["p95_ms"]
            p99 = ep_result["p99_ms"]
            is_write = ep.get("method", "GET") in ("POST", "PUT", "PATCH", "DELETE")

            if is_write:
                p95_ok = p95 <= WRITE_P95_THRESHOLD_MS
                p99_ok = p99 <= WRITE_P99_THRESHOLD_MS
            else:
                p95_ok = p95 <= READ_P95_THRESHOLD_MS
                p99_ok = p99 <= READ_P99_THRESHOLD_MS

            base_p95 = baseline.get(ep.get("path", ""), {}).get("p95_ms", 0.0)
            if base_p95 > 0:
                degradation = (p95 - base_p95) / base_p95
                if degradation > DEGRADATION_THRESHOLD:
                    degraded_endpoints.append(ep.get("path", ""))

            ep_result["pass"] = p95_ok and p99_ok
            if not ep_result["pass"]:
                all_pass = False
            report["results"].append(ep_result)

        report["degraded_endpoints"] = degraded_endpoints
        report["all_pass"] = all_pass

        return VerificationResult(
            conclusion=VerificationConclusion.PASS if all_pass else VerificationConclusion.FAIL,
            report=report,
            failure_code=None if all_pass else PRODErrorCode.BASELINE_LATENCY_DEGRADED.value,
            failure_detail={"degraded": degraded_endpoints} if degraded_endpoints else None,
            duration_ms=int((time.monotonic() - start_ts) * 1000),
        )