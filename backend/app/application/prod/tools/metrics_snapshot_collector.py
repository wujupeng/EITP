"""Prometheus 指标快照采集器。"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MetricsSnapshot:
    """指标快照结果。"""

    promql: str
    start: float
    end: float
    step: str
    data: dict[str, Any]
    content_hash: str
    captured_at: datetime


class MetricsSnapshotCollector:
    """指标快照采集器。

    输入采集时间窗口 + PromQL → 查询 Prometheus Range Query →
    序列化指标快照至 JSON → 计算快照 content_hash（SHA-256）→ 存储
    """

    def __init__(self, prometheus_url: str = "http://localhost:9090") -> None:
        self._prometheus_url = prometheus_url.rstrip("/")

    async def collect_range(
        self,
        promql: str,
        start: float,
        end: float,
        step: str = "15s",
    ) -> MetricsSnapshot:
        url = f"{self._prometheus_url}/api/v1/query_range"
        params = {
            "query": promql,
            "start": str(start),
            "end": str(end),
            "step": step,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        snapshot_json = json.dumps(data, sort_keys=True, ensure_ascii=False)
        content_hash = hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest()

        snapshot = MetricsSnapshot(
            promql=promql,
            start=start,
            end=end,
            step=step,
            data=data,
            content_hash=content_hash,
            captured_at=datetime.now(timezone.utc),
        )
        logger.info("Metrics snapshot collected: promql=%s, hash=%s", promql, content_hash)
        return snapshot

    async def collect_instant(self, promql: str) -> dict[str, Any]:
        url = f"{self._prometheus_url}/api/v1/query"
        params = {"query": promql}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    async def collect_multiple(
        self,
        queries: list[str],
        start: float,
        end: float,
        step: str = "15s",
    ) -> list[MetricsSnapshot]:
        import asyncio
        tasks = [self.collect_range(q, start, end, step) for q in queries]
        return await asyncio.gather(*tasks, return_exceptions=False)