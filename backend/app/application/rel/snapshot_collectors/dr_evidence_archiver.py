"""灾备证据归档采集器 - DrEvidenceArchiver。"""

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


class DrEvidenceArchiver(AssetSnapshotCollector):
    """灾备证据归档采集器（5.14）。"""

    def __init__(
        self,
        snapshot_repository: AssetSnapshotRepository,
        archive_client: ArchiveStorageClient,
        dr_executor: object | None = None,
    ) -> None:
        super().__init__(AssetType.DR_EVIDENCE, snapshot_repository, archive_client)
        self._dr_executor = dr_executor

    async def collect(self, release_id: UUID, collected_by: str) -> AssetSnapshotAggregate:
        evidence = {}
        if self._dr_executor is not None:
            evidence = await self._dr_executor.collect_dr_evidence()
        content = json.dumps(evidence, sort_keys=True, default=str).encode("utf-8")
        return await self._archive_and_index(
            release_id=release_id,
            asset_name="dr_evidence",
            content=content,
            collected_by=collected_by,
        )