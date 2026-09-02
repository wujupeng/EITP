"""DDL 全量快照导出采集器 - DdlFullSnapshotExporter。"""

from __future__ import annotations

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


class DdlFullSnapshotExporter(AssetSnapshotCollector):
    """DDL 全量快照导出采集器（5.3）。"""

    def __init__(
        self,
        snapshot_repository: AssetSnapshotRepository,
        archive_client: ArchiveStorageClient,
        alembic_client: AlembicClient,
        database_url: str,
    ) -> None:
        super().__init__(AssetType.DDL_SNAPSHOT, snapshot_repository, archive_client)
        self._alembic_client = alembic_client
        self._database_url = database_url

    async def collect(self, release_id: UUID, collected_by: str) -> AssetSnapshotAggregate:
        ddl = await self._alembic_client.export_ddl(self._database_url)

        if not ddl or "CREATE TABLE" not in ddl:
            raise RELError(
                RELErrorCode.DDL_INCOMPLETE,
                "DDL snapshot incomplete: missing CREATE TABLE statements",
            )

        content = ddl.encode("utf-8")
        return await self._archive_and_index(
            release_id=release_id,
            asset_name="ddl_full_snapshot",
            content=content,
            collected_by=collected_by,
        )