"""AssetSnapshotCollector 基类单元测试 - _archive_and_index 归档与索引流程。

覆盖 application/rel/snapshot_collectors/asset_snapshot_collector.py 的
AssetSnapshotCollector 抽象基类的 _archive_and_index 方法：
- 调用 archive_client.archive → AssetSnapshotAggregate.create → snapshot_repo.save
- asset_type 属性
- 抽象方法 collect 未实现
- 内容哈希/位置/大小透传
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from app.application.rel.snapshot_collectors.asset_snapshot_collector import (
    AssetSnapshotCollector,
)
from app.domain.rel.aggregates.asset_snapshot_aggregate import AssetSnapshotAggregate
from app.domain.rel.enums import AssetType, VerificationStatus
from app.infrastructure.rel.asset_snapshot_repository import AssetSnapshotRepository
from app.infrastructure.rel.clients.archive_storage_client import (
    ArchiveResult,
    ArchiveStorageClient,
)


class _ConcreteCollector(AssetSnapshotCollector):
    """用于测试基类 _archive_and_index 的具体子类。"""

    async def collect(self, release_id: UUID, collected_by: str) -> AssetSnapshotAggregate:
        return await self._archive_and_index(
            release_id=release_id,
            asset_name="test_asset",
            content=b"hello",
            collected_by=collected_by,
        )


def _make_collector() -> tuple[_ConcreteCollector, AsyncMock, AsyncMock]:
    snapshot_repo = AsyncMock(spec=AssetSnapshotRepository)
    archive_client = AsyncMock(spec=ArchiveStorageClient)
    archive_client.archive = AsyncMock(
        return_value=ArchiveResult(
            location="/archive/test_asset.bin",
            content_hash="a" * 64,
            size_bytes=5,
        )
    )
    collector = _ConcreteCollector(
        asset_type=AssetType.GIT_TAG,
        snapshot_repository=snapshot_repo,
        archive_client=archive_client,
    )
    return collector, snapshot_repo, archive_client


class AssetSnapshotCollectorTest:
    """AssetSnapshotCollector 基类 _archive_and_index 测试。"""

    async def test_asset_type_property_returns_configured_type(self) -> None:
        collector, _, _ = _make_collector()
        assert collector.asset_type == AssetType.GIT_TAG

    async def test_collect_archives_and_indexes_and_saves(self) -> None:
        collector, snapshot_repo, archive_client = _make_collector()
        release_id = uuid4()
        snapshot = await collector.collect(release_id, "alice")

        archive_client.archive.assert_awaited_once_with("test_asset", b"hello")
        snapshot_repo.save.assert_awaited_once()
        assert isinstance(snapshot, AssetSnapshotAggregate)

    async def test_collect_propagates_archive_hash_and_location(self) -> None:
        collector, _, _ = _make_collector()
        snapshot = await collector.collect(uuid4(), "alice")
        assert snapshot.asset_content_hash == "a" * 64
        assert snapshot.archive_location == "/archive/test_asset.bin"
        assert snapshot.archive_size_bytes == 5

    async def test_collect_creates_snapshot_with_correct_metadata(self) -> None:
        collector, _, _ = _make_collector()
        release_id = uuid4()
        snapshot = await collector.collect(release_id, "bob")
        assert snapshot.release_id == release_id
        assert snapshot.asset_type == AssetType.GIT_TAG
        assert snapshot.asset_name == "test_asset"
        assert snapshot.collected_by == "bob"
        assert snapshot.verification_status == VerificationStatus.VERIFIED

    async def test_collect_generates_unique_snapshot_id(self) -> None:
        collector, _, _ = _make_collector()
        a = await collector.collect(uuid4(), "alice")
        b = await collector.collect(uuid4(), "alice")
        assert a.snapshot_id != b.snapshot_id

    async def test_base_class_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            AssetSnapshotCollector(  # type: ignore[abstract]
                asset_type=AssetType.GIT_TAG,
                snapshot_repository=AsyncMock(),
                archive_client=AsyncMock(),
            )

    async def test_collect_passes_content_to_archive_client(self) -> None:
        snapshot_repo = AsyncMock(spec=AssetSnapshotRepository)
        archive_client = AsyncMock(spec=ArchiveStorageClient)
        archive_client.archive = AsyncMock(
            return_value=ArchiveResult(location="/x", content_hash="h", size_bytes=10)
        )

        class _ContentCollector(AssetSnapshotCollector):
            async def collect(self, release_id: UUID, collected_by: str) -> AssetSnapshotAggregate:
                return await self._archive_and_index(
                    release_id=release_id,
                    asset_name="named",
                    content=b"specific-content",
                    collected_by=collected_by,
                )

        collector = _ContentCollector(AssetType.DDL_SNAPSHOT, snapshot_repo, archive_client)
        await collector.collect(uuid4(), "alice")
        archive_client.archive.assert_awaited_once_with("named", b"specific-content")