"""PROD 证明书快照采集器 - ProdDossierSnapshotCollector。"""

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
from app.infrastructure.rel.clients.archive_storage_client import ArchiveStorageClient


class ProdDossierSnapshotCollector(AssetSnapshotCollector):
    """PROD 证明书快照采集器（5.8）。"""

    def __init__(
        self,
        snapshot_repository: AssetSnapshotRepository,
        archive_client: ArchiveStorageClient,
        dossier_repository: object | None = None,
    ) -> None:
        super().__init__(AssetType.PROD_DOSSIER, snapshot_repository, archive_client)
        self._dossier_repo = dossier_repository

    async def collect(self, release_id: UUID, collected_by: str) -> AssetSnapshotAggregate:
        dossiers = []
        if self._dossier_repo is not None:
            dossiers = await self._dossier_repo.list_all_dossiers()
            for d in dossiers:
                if not d.get("signer"):
                    raise RELError(
                        RELErrorCode.PROD_DOSSIER_NOT_SIGNED,
                        f"dossier {d.get('dossier_id')} not signed",
                    )
        content = json.dumps(dossiers, sort_keys=True, default=str).encode("utf-8")
        return await self._archive_and_index(
            release_id=release_id,
            asset_name="prod_dossier_archive",
            content=content,
            collected_by=collected_by,
        )