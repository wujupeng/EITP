"""SEC 证书快照采集器 - SecCertSnapshotCollector。"""

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


class SecCertSnapshotCollector(AssetSnapshotCollector):
    """SEC 证书快照采集器（5.7）。"""

    def __init__(
        self,
        snapshot_repository: AssetSnapshotRepository,
        archive_client: ArchiveStorageClient,
        sec_cert_repository: object | None = None,
    ) -> None:
        super().__init__(AssetType.SEC_CERT, snapshot_repository, archive_client)
        self._sec_cert_repo = sec_cert_repository

    async def collect(self, release_id: UUID, collected_by: str) -> AssetSnapshotAggregate:
        certs = []
        if self._sec_cert_repo is not None:
            certs = await self._sec_cert_repo.list_all_certs()
        content = json.dumps(certs, sort_keys=True, default=str).encode("utf-8")
        return await self._archive_and_index(
            release_id=release_id,
            asset_name="sec_cert_archive",
            content=content,
            collected_by=collected_by,
        )