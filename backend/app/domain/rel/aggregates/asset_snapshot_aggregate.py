"""REL 资产快照聚合根 - AssetSnapshotAggregate。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.rel.enums import AssetType, VerificationStatus
from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError


@dataclass(frozen=True)
class AssetSnapshotAggregate:
    """资产快照聚合根 - append-only 不可变。"""

    snapshot_id: UUID
    release_id: UUID
    asset_type: AssetType
    asset_name: str
    asset_content_hash: str
    archive_location: str
    archive_time: datetime
    archive_size_bytes: int
    collected_by: str
    verification_status: VerificationStatus = VerificationStatus.VERIFIED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        release_id: UUID,
        asset_type: AssetType,
        asset_name: str,
        asset_content_hash: str,
        archive_location: str,
        archive_size_bytes: int,
        collected_by: str,
    ) -> AssetSnapshotAggregate:
        return cls(
            snapshot_id=uuid4(),
            release_id=release_id,
            asset_type=asset_type,
            asset_name=asset_name,
            asset_content_hash=asset_content_hash,
            archive_location=archive_location,
            archive_time=datetime.now(timezone.utc),
            archive_size_bytes=archive_size_bytes,
            collected_by=collected_by,
        )

    def mark_tampered(self) -> AssetSnapshotAggregate:
        if self.verification_status == VerificationStatus.TAMPERED:
            return self
        from dataclasses import replace
        return replace(self, verification_status=VerificationStatus.TAMPERED)