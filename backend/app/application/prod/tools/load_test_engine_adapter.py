"""压测引擎适配器基类。"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoadTestResult:
    """压测结果。"""

    engine: str
    started_at: datetime
    finished_at: datetime
    total_requests: int
    success_count: int
    failure_count: int
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    qps: float
    error_rate: float
    raw_output: dict[str, Any] = field(default_factory=dict)


class LoadTestEngineAdapter(ABC):
    """压测引擎适配器基类。

    按场景选择压测引擎 → 下发负载 → 采集结果 → 资源占用 ≤5% 约束
    """

    @property
    @abstractmethod
    def engine_name(self) -> str: ...

    @abstractmethod
    async def _run_engine(self, target_url: str, duration_seconds: int, concurrency: int, **kwargs: Any) -> dict[str, Any]: ...

    async def execute(
        self,
        target_url: str,
        duration_seconds: int = 60,
        concurrency: int = 10,
        **kwargs: Any,
    ) -> LoadTestResult:
        started_at = datetime.now(timezone.utc)
        logger.info("Load test [%s] starting: url=%s, duration=%ds, concurrency=%d",
                     self.engine_name, target_url, duration_seconds, concurrency)

        raw = await self._run_engine(target_url, duration_seconds, concurrency, **kwargs)

        finished_at = datetime.now(timezone.utc)
        total = raw.get("total_requests", 0)
        success = raw.get("success_count", 0)
        failure = total - success

        result = LoadTestResult(
            engine=self.engine_name,
            started_at=started_at,
            finished_at=finished_at,
            total_requests=total,
            success_count=success,
            failure_count=failure,
            p50_latency_ms=raw.get("p50_ms", 0.0),
            p95_latency_ms=raw.get("p95_ms", 0.0),
            p99_latency_ms=raw.get("p99_ms", 0.0),
            qps=raw.get("qps", 0.0),
            error_rate=failure / total if total > 0 else 0.0,
            raw_output=raw,
        )
        logger.info("Load test [%s] completed: qps=%.1f, p95=%.1fms, error_rate=%.4f",
                     self.engine_name, result.qps, result.p95_latency_ms, result.error_rate)
        return result