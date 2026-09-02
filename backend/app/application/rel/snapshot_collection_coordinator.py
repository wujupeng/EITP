"""快照采集协调器 - SnapshotCollectionCoordinator。"""

from __future__ import annotations

import asyncio
from uuid import UUID

from structlog import get_logger

from app.application.rel.snapshot_collectors.asset_snapshot_collector import (
    AssetSnapshotCollector,
)

logger = get_logger(__name__)


class SnapshotCollectionCoordinator:
    """协调 14 项资产快照采集器并行执行。"""

    def __init__(self, collectors: list[AssetSnapshotCollector]) -> None:
        self._collectors = collectors

    async def collect_all(
        self,
        release_id: UUID,
        collected_by: str,
    ) -> list[dict]:
        tasks = [
            collector.collect(release_id, collected_by)
            for collector in self._collectors
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        snapshots: list[dict] = []
        for i, result in enumerate(results):
            collector = self._collectors[i]
            if isinstance(result, Exception):
                logger.error(
                    "snapshot_collection_failed",
                    release_id=str(release_id),
                    asset_type=collector.asset_type.value,
                    error=str(result),
                )
                raise result
            snapshots.append({
                "asset_type": collector.asset_type.value,
                "snapshot_id": str(result.snapshot_id),
                "content_hash": result.asset_content_hash,
                "archive_location": result.archive_location,
                "size_bytes": result.archive_size_bytes,
            })
            logger.info(
                "snapshot_collected",
                release_id=str(release_id),
                asset_type=collector.asset_type.value,
            )
        return snapshots