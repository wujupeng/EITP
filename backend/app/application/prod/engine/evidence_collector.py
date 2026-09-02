"""证据采集器 - 采集证据三元组并写入持久化。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID

from app.application.prod.engine.evidence_hash_calculator import (
    EvidenceHashCalculator,
    EvidenceTriplet,
)
from app.domain.prod.engine.enums import EvidenceType

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CollectedEvidence:
    """采集到的证据三元组结果。"""

    triplet: EvidenceTriplet
    report_path: str
    metrics_snapshot_path: str
    log_path: str
    report_size: int
    metrics_size: int
    log_size: int
    collected_at: datetime


class EvidenceStorage(Protocol):
    """证据存储接口。"""

    async def store(self, run_id: UUID, evidence_type: str, content: bytes, content_hash: str) -> str:
        """存储证据内容，返回存储路径。"""
        ...


class MetricsQuerier(Protocol):
    """Prometheus 指标查询接口。"""

    async def range_query(self, promql: str, start: float, end: float, step: str) -> dict:
        """Prometheus Range Query。"""
        ...


class LogRetriever(Protocol):
    """结构化日志检索接口。"""

    async def retrieve_by_trace_id(self, trace_id: str) -> bytes:
        """按 TraceId 检索结构化日志。"""
        ...


class EvidenceCollector:
    """证据采集器。

    采集证据三元组:
    - 证据1: 结构化验证报告 JSON
    - 证据2: Prometheus 指标快照
    - 证据3: 结构化日志（按 trace_id 检索）
    """

    def __init__(
        self,
        storage: EvidenceStorage,
        metrics_querier: MetricsQuerier | None = None,
        log_retriever: LogRetriever | None = None,
    ) -> None:
        self._storage = storage
        self._metrics_querier = metrics_querier
        self._log_retriever = log_retriever

    async def collect(
        self,
        run_id: UUID,
        tenant_id: UUID,
        trace_id: str,
        report: dict[str, Any],
        metrics_promql: str | None = None,
        metrics_time_window: tuple[float, float] | None = None,
    ) -> CollectedEvidence:
        report_bytes = json.dumps(report, sort_keys=True, ensure_ascii=False).encode("utf-8")
        report_hash = EvidenceHashCalculator.compute_content_hash(report_bytes)
        report_path = await self._storage.store(
            run_id, EvidenceType.REPORT.value, report_bytes, report_hash
        )

        if self._metrics_querier and metrics_promql and metrics_time_window:
            metrics_data = await self._metrics_querier.range_query(
                metrics_promql,
                metrics_time_window[0],
                metrics_time_window[1],
                "15s",
            )
        else:
            metrics_data = {"note": "metrics not available", "trace_id": trace_id}
        metrics_bytes = json.dumps(metrics_data, sort_keys=True, ensure_ascii=False).encode("utf-8")
        metrics_hash = EvidenceHashCalculator.compute_content_hash(metrics_bytes)
        metrics_path = await self._storage.store(
            run_id, EvidenceType.METRICS_SNAPSHOT.value, metrics_bytes, metrics_hash
        )

        if self._log_retriever:
            log_bytes = await self._log_retriever.retrieve_by_trace_id(trace_id)
        else:
            log_bytes = json.dumps(
                {"note": "log retriever not available", "trace_id": trace_id}
            ).encode("utf-8")
        log_hash = EvidenceHashCalculator.compute_content_hash(log_bytes)
        log_path = await self._storage.store(
            run_id, EvidenceType.LOG.value, log_bytes, log_hash
        )

        triplet = EvidenceTriplet(
            report_hash=report_hash,
            metrics_snapshot_hash=metrics_hash,
            log_hash=log_hash,
        )

        logger.info(
            "Evidence collected for run %s (trace_id=%s): aggregate_hash=%s",
            run_id,
            trace_id,
            triplet.aggregate_hash,
        )

        return CollectedEvidence(
            triplet=triplet,
            report_path=report_path,
            metrics_snapshot_path=metrics_path,
            log_path=log_path,
            report_size=len(report_bytes),
            metrics_size=len(metrics_bytes),
            log_size=len(log_bytes),
            collected_at=datetime.now(timezone.utc),
        )