"""RLS 基线快照采集器 - RlsBaselineSnapshotCollector。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.rel.snapshot_collectors.asset_snapshot_collector import (
    AssetSnapshotCollector,
)
from app.domain.rel.aggregates.asset_snapshot_aggregate import AssetSnapshotAggregate
from app.domain.rel.enums import AssetType
from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError
from app.infrastructure.rel.asset_snapshot_repository import AssetSnapshotRepository
from app.infrastructure.rel.clients.archive_storage_client import ArchiveStorageClient


class RlsBaselineSnapshotCollector(AssetSnapshotCollector):
    """RLS 基线快照采集器（5.6）。"""

    def __init__(
        self,
        snapshot_repository: AssetSnapshotRepository,
        archive_client: ArchiveStorageClient,
        session: AsyncSession,
    ) -> None:
        super().__init__(AssetType.RLS_BASELINE, snapshot_repository, archive_client)
        self._session = session

    async def collect(self, release_id: UUID, collected_by: str) -> AssetSnapshotAggregate:
        result = await self._session.execute(
            text(
                "SELECT schemaname, tablename, policyname, permissive, roles, "
                "cmd, qual, with_check FROM pg_policies "
                "WHERE schemaname = 'public' ORDER BY tablename, policyname"
            )
        )
        policies = []
        for row in result.fetchall():
            policies.append(dict(row._mapping))

        import json
        content = json.dumps(policies, sort_keys=True).encode("utf-8")
        return await self._archive_and_index(
            release_id=release_id,
            asset_name="rls_baseline_snapshot",
            content=content,
            collected_by=collected_by,
        )