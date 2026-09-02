"""测试结果归档采集器 - TestResultArchiver。"""

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


class TestResultArchiver(AssetSnapshotCollector):
    """测试结果归档采集器（5.9）。"""

    def __init__(
        self,
        snapshot_repository: AssetSnapshotRepository,
        archive_client: ArchiveStorageClient,
        test_runner: object | None = None,
    ) -> None:
        super().__init__(AssetType.TEST_RESULT, snapshot_repository, archive_client)
        self._test_runner = test_runner

    async def collect(self, release_id: UUID, collected_by: str) -> AssetSnapshotAggregate:
        result = {}
        if self._test_runner is not None:
            result = await self._test_runner.run_all()

        if result.get("failed", 0) > 0:
            raise RELError(
                RELErrorCode.TEST_RESULT_HAS_FAILURE,
                f"{result['failed']} test(s) failed",
            )

        content = json.dumps(result, sort_keys=True, default=str).encode("utf-8")
        return await self._archive_and_index(
            release_id=release_id,
            asset_name="test_result_378",
            content=content,
            collected_by=collected_by,
        )