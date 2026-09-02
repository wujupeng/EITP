"""权限矩阵快照采集器 - PermissionMatrixSnapshotCollector。"""

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


class PermissionMatrixSnapshotCollector(AssetSnapshotCollector):
    """权限矩阵快照采集器（5.5）。"""

    def __init__(
        self,
        snapshot_repository: AssetSnapshotRepository,
        archive_client: ArchiveStorageClient,
        permission_repository: object | None = None,
    ) -> None:
        super().__init__(AssetType.PERMISSION_MATRIX, snapshot_repository, archive_client)
        self._permission_repo = permission_repository

    async def collect(self, release_id: UUID, collected_by: str) -> AssetSnapshotAggregate:
        matrix = {}
        if self._permission_repo is not None:
            matrix = await self._permission_repo.export_full_matrix()
        content = json.dumps(matrix, sort_keys=True).encode("utf-8")
        return await self._archive_and_index(
            release_id=release_id,
            asset_name="permission_matrix_snapshot",
            content=content,
            collected_by=collected_by,
        )