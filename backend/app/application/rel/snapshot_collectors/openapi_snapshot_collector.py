"""OpenAPI 规范快照采集器 - OpenApiSnapshotCollector。"""

from __future__ import annotations

import json
from uuid import UUID

import httpx

from app.application.rel.snapshot_collectors.asset_snapshot_collector import (
    AssetSnapshotCollector,
)
from app.domain.rel.aggregates.asset_snapshot_aggregate import AssetSnapshotAggregate
from app.domain.rel.enums import AssetType
from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError
from app.infrastructure.rel.asset_snapshot_repository import AssetSnapshotRepository
from app.infrastructure.rel.clients.archive_storage_client import ArchiveStorageClient


class OpenApiSnapshotCollector(AssetSnapshotCollector):
    """OpenAPI 规范快照采集器（5.4）。"""

    def __init__(
        self,
        snapshot_repository: AssetSnapshotRepository,
        archive_client: ArchiveStorageClient,
        app_base_url: str = "http://localhost:8000",
    ) -> None:
        super().__init__(AssetType.OPENAPI, snapshot_repository, archive_client)
        self._app_base_url = app_base_url.rstrip("/")

    async def collect(self, release_id: UUID, collected_by: str) -> AssetSnapshotAggregate:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self._app_base_url}/openapi.json")

        if resp.status_code != 200:
            raise RELError(
                RELErrorCode.DDL_EXPORT_FAILED,
                f"OpenAPI fetch failed: {resp.status_code}",
            )

        openapi_json = resp.json()
        content = json.dumps(openapi_json, sort_keys=True).encode("utf-8")

        return await self._archive_and_index(
            release_id=release_id,
            asset_name="openapi_spec_v1.0.0",
            content=content,
            collected_by=collected_by,
        )