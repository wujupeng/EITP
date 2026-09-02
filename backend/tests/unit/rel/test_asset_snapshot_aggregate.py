"""AssetSnapshotAggregate 单元测试 - 创建 / tampered 标记 / 不可变性 / append-only。

覆盖 domain/rel/aggregates/asset_snapshot_aggregate.py 的 create() 初始态、
默认 VERIFIED、mark_tampered 转换、幂等标记、frozen 不可变性、UUID 生成。
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass
from uuid import UUID, uuid4

import pytest

from app.domain.rel.aggregates.asset_snapshot_aggregate import AssetSnapshotAggregate
from app.domain.rel.enums import AssetType, VerificationStatus


def _make_snapshot() -> AssetSnapshotAggregate:
    return AssetSnapshotAggregate.create(
        release_id=uuid4(),
        asset_type=AssetType.GIT_TAG,
        asset_name="git_tag_v1.0.0",
        asset_content_hash="a" * 64,
        archive_location="/archive/git_tag_v1.0.0.bin",
        archive_size_bytes=1024,
        collected_by="alice",
    )


class AssetSnapshotAggregateTest:
    """AssetSnapshotAggregate 创建与篡改标记测试。"""

    # --- create() ---

    def test_create_generates_snapshot_id(self) -> None:
        snap = _make_snapshot()
        assert isinstance(snap.snapshot_id, UUID)

    def test_create_initial_verification_status_is_verified(self) -> None:
        snap = _make_snapshot()
        assert snap.verification_status == VerificationStatus.VERIFIED

    def test_create_preserves_asset_metadata(self) -> None:
        release_id = uuid4()
        snap = AssetSnapshotAggregate.create(
            release_id=release_id,
            asset_type=AssetType.DDL_SNAPSHOT,
            asset_name="ddl.sql",
            asset_content_hash="b" * 64,
            archive_location="/x",
            archive_size_bytes=2048,
            collected_by="bob",
        )
        assert snap.release_id == release_id
        assert snap.asset_type == AssetType.DDL_SNAPSHOT
        assert snap.asset_name == "ddl.sql"
        assert snap.asset_content_hash == "b" * 64
        assert snap.archive_location == "/x"
        assert snap.archive_size_bytes == 2048
        assert snap.collected_by == "bob"

    def test_create_sets_archive_time(self) -> None:
        snap = _make_snapshot()
        assert snap.archive_time is not None

    def test_create_generates_unique_snapshot_ids(self) -> None:
        a = _make_snapshot()
        b = _make_snapshot()
        assert a.snapshot_id != b.snapshot_id

    # --- mark_tampered() ---

    def test_mark_tampered_transitions_to_tampered(self) -> None:
        snap = _make_snapshot().mark_tampered()
        assert snap.verification_status == VerificationStatus.TAMPERED

    def test_mark_tampered_is_idempotent(self) -> None:
        snap = _make_snapshot().mark_tampered()
        again = snap.mark_tampered()
        assert again.verification_status == VerificationStatus.TAMPERED
        assert again is snap

    def test_mark_tampered_returns_new_instance_when_verified(self) -> None:
        snap = _make_snapshot()
        tampered = snap.mark_tampered()
        assert snap.verification_status == VerificationStatus.VERIFIED
        assert tampered.verification_status == VerificationStatus.TAMPERED
        assert snap is not tampered

    # --- 不可变性 ---

    def test_frozen_dataclass_is_immutable(self) -> None:
        snap = _make_snapshot()
        assert is_dataclass(snap)
        with pytest.raises(FrozenInstanceError):
            snap.verification_status = VerificationStatus.TAMPERED  # type: ignore[misc]

    def test_asset_type_can_be_any_of_fifteen(self) -> None:
        for asset_type in AssetType:
            snap = AssetSnapshotAggregate.create(
                release_id=uuid4(),
                asset_type=asset_type,
                asset_name=f"name_{asset_type.value}",
                asset_content_hash="h",
                archive_location="/l",
                archive_size_bytes=1,
                collected_by="c",
            )
            assert snap.asset_type == asset_type