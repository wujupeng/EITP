"""资产快照采集器基类 - AssetSnapshotCollector。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from structlog import get_logger

from app.domain.rel.aggregates.asset_snapshot_aggregate import AssetSnapshotAggregate
from app.domain.rel.enums import AssetType
from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError
from app.infrastructure.rel.asset_snapshot_repository import AssetSnapshotRepository
from app.infrastructure.rel.clients.archive_storage_client import ArchiveStorageClient

logger = get_logger(__name__)


class AssetSnapshotCollector(ABC):
    """资产快照采集器抽象基类。"""

    def __init__(
        self,
        asset_type: AssetType,
        snapshot_repository: AssetSnapshotRepository,
        archive_client: ArchiveStorageClient,
    ) -> None:
        self._asset_type = asset_type
        self._snapshot_repo = snapshot_repository
        self._archive_client = archive_client

    @property
    def asset_type(self) -> AssetType:
        return self._asset_type

    @abstractmethod
    async def collect(self, release_id: UUID, collected_by: str) -> AssetSnapshotAggregate:
        """子类实现具体采集逻辑，返回资产内容 bytes。"""
        ...

    async def _archive_and_index(
        self,
        release_id: UUID,
        asset_name: str,
        content: bytes,
        collected_by: str,
    ) -> AssetSnapshotAggregate:
        archive_result = await self._archive_client.archive(asset_name, content)

        snapshot = AssetSnapshotAggregate.create(
            release_id=release_id,
            asset_type=self._asset_type,
            asset_name=asset_name,
            asset_content_hash=archive_result.content_hash,
            archive_location=archive_result.location,
            archive_size_bytes=archive_result.size_bytes,
            collected_by=collected_by,
        )
        await self._snapshot_repo.save(snapshot)

        logger.info(
            "asset_snapshot_collected",
            release_id=str(release_id),
            asset_type=self._asset_type.value,
            asset_name=asset_name,
            content_hash=archive_result.content_hash,
            size_bytes=archive_result.size_bytes,
        )
        return snapshot