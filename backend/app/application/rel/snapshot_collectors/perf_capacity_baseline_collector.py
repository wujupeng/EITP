"""性能容量基线采集器 - PerfCapacityBaselineCollector。"""

from __future__ import annotations

import json
from uuid import UUID

from app.application.rel.snapshot_collectors.asset_snapshot_collector import (
    AssetSnapshotCollector,
)
from app.domain.rel.aggregates.asset_snapshot_aggregate import AssetSnapshotAggregate
from app.domain.rel.enums import AssetType
from app.infrastructure.rel.asset_snapshot_repository import AssetSnapshotRepository
from app.infrastructure.rel.clients.archive_storage_client import ArchiveStorageClient


class PerfCapacityBaselineCollector(AssetSnapshotCollector):
    """性能容量基线采集器（5.10）。"""

    def __init__(
        self,
        snapshot_repository: AssetSnapshotRepository,
        archive_client: ArchiveStorageClient,
        baseline_collector: object | None = None,
    ) -> None:
        super().__init__(AssetType.PERF_CAPACITY_BASELINE, snapshot_repository, archive_client)
        self._baseline_collector = baseline_collector

    async def collect(self, release_id: UUID, collected_by: str) -> AssetSnapshotAggregate:
        baseline = {}
        if self._baseline_collector is not None:
            baseline = await self._baseline_collector.collect_current_baseline()
        content = json.dumps(baseline, sort_keys=True, default=str).encode("utf-8")
        return await self._archive_and_index(
            release_id=release_id,
            asset_name="perf_capacity_baseline",
            content=content,
            collected_by=collected_by,
        )