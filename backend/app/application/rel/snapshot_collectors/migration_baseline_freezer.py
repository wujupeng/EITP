"""迁移基线固化采集器 - MigrationBaselineFreezer。"""

from __future__ import annotations

import json
from uuid import UUID

from app.application.rel.snapshot_collectors.asset_snapshot_collector import (
    AssetSnapshotCollector,
)
from app.domain.rel.aggregates.asset_snapshot_aggregate import AssetSnapshotAggregate
from app.domain.rel.enums import AssetType
from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError
from app.infrastructure.rel.asset_snapshot_repository import AssetSnapshotRepository
from app.infrastructure.rel.clients.alembic_client import AlembicClient
from app.infrastructure.rel.clients.archive_storage_client import ArchiveStorageClient


class MigrationBaselineFreezer(AssetSnapshotCollector):
    """迁移基线固化采集器（5.3）。"""

    def __init__(
        self,
        snapshot_repository: AssetSnapshotRepository,
        archive_client: ArchiveStorageClient,
        alembic_client: AlembicClient,
    ) -> None:
        super().__init__(AssetType.MIGRATION_BASELINE, snapshot_repository, archive_client)
        self._alembic_client = alembic_client

    async def collect(self, release_id: UUID, collected_by: str) -> AssetSnapshotAggregate:
        baseline = await self._alembic_client.scan_migrations()

        if not baseline.chain_valid:
            raise RELError(
                RELErrorCode.MIGRATION_CHAIN_BROKEN,
                f"migration chain broken at revision {baseline.broken_at}",
            )

        content = json.dumps({
            "baseline_hash": baseline.baseline_hash,
            "files": [
                {
                    "revision": f.revision,
                    "down_revision": f.down_revision,
                    "file_hash": f.file_hash,
                    "file_path": f.file_path,
                }
                for f in baseline.files
            ],
        }, sort_keys=True).encode("utf-8")

        return await self._archive_and_index(
            release_id=release_id,
            asset_name="migration_baseline_001-064",
            content=content,
            collected_by=collected_by,
        )