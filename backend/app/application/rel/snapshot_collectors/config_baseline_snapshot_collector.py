"""配置基线快照采集器 - ConfigBaselineSnapshotCollector。"""

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


class ConfigBaselineSnapshotCollector(AssetSnapshotCollector):
    """配置基线快照采集器（5.12）。"""

    def __init__(
        self,
        snapshot_repository: AssetSnapshotRepository,
        archive_client: ArchiveStorageClient,
        config_repository: object | None = None,
    ) -> None:
        super().__init__(AssetType.CONFIG_BASELINE, snapshot_repository, archive_client)
        self._config_repo = config_repository

    async def collect(self, release_id: UUID, collected_by: str) -> AssetSnapshotAggregate:
        config = {}
        if self._config_repo is not None:
            config = await self._config_repo.export_all_namespaces()
        content = json.dumps(config, sort_keys=True, default=str).encode("utf-8")
        return await self._archive_and_index(
            release_id=release_id,
            asset_name="config_baseline",
            content=content,
            collected_by=collected_by,
        )