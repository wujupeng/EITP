"""备份证据归档采集器 - BackupEvidenceArchiver。"""

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


class BackupEvidenceArchiver(AssetSnapshotCollector):
    """备份证据归档采集器（5.13）。"""

    def __init__(
        self,
        snapshot_repository: AssetSnapshotRepository,
        archive_client: ArchiveStorageClient,
        backup_executor: object | None = None,
    ) -> None:
        super().__init__(AssetType.BACKUP_EVIDENCE, snapshot_repository, archive_client)
        self._backup_executor = backup_executor

    async def collect(self, release_id: UUID, collected_by: str) -> AssetSnapshotAggregate:
        evidence = {}
        if self._backup_executor is not None:
            evidence = await self._backup_executor.collect_backup_evidence()
        content = json.dumps(evidence, sort_keys=True, default=str).encode("utf-8")
        return await self._archive_and_index(
            release_id=release_id,
            asset_name="backup_evidence",
            content=content,
            collected_by=collected_by,
        )