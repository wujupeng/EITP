"""REL 资产快照仓储 - 仅 INSERT，无 update/delete。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.rel.aggregates.asset_snapshot_aggregate import AssetSnapshotAggregate


class AssetSnapshotRepository:
    """资产快照仓储 - append-only。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, snapshot: AssetSnapshotAggregate) -> None:
        await self._session.execute(
            text(
                "INSERT INTO rel_asset_snapshot "
                "(snapshot_id, release_id, asset_type, asset_name, asset_content_hash, "
                "archive_location, archive_time, archive_size_bytes, collected_by, "
                "verification_status, created_at) "
                "VALUES (:snapshot_id, :release_id, :asset_type, :asset_name, :asset_content_hash, "
                ":archive_location, :archive_time, :archive_size_bytes, :collected_by, "
                ":verification_status, :created_at)"
            ),
            {
                "snapshot_id": str(snapshot.snapshot_id),
                "release_id": str(snapshot.release_id),
                "asset_type": snapshot.asset_type.value,
                "asset_name": snapshot.asset_name,
                "asset_content_hash": snapshot.asset_content_hash,
                "archive_location": snapshot.archive_location,
                "archive_time": snapshot.archive_time,
                "archive_size_bytes": snapshot.archive_size_bytes,
                "collected_by": snapshot.collected_by,
                "verification_status": snapshot.verification_status.value,
                "created_at": snapshot.created_at,
            },
        )

    async def get_by_release(self, release_id: UUID) -> list[dict]:
        result = await self._session.execute(
            text(
                "SELECT * FROM rel_asset_snapshot "
                "WHERE release_id = :release_id ORDER BY created_at ASC"
            ),
            {"release_id": str(release_id)},
        )
        return [dict(row._mapping) for row in result.fetchall()]

    async def get_by_id(self, snapshot_id: UUID) -> dict | None:
        result = await self._session.execute(
            text("SELECT * FROM rel_asset_snapshot WHERE snapshot_id = :snapshot_id"),
            {"snapshot_id": str(snapshot_id)},
        )
        row = result.first()
        return dict(row._mapping) if row else None

    async def verify_hash(self, release_id: UUID) -> bool:
        result = await self._session.execute(
            text(
                "SELECT COUNT(*) as cnt FROM rel_asset_snapshot "
                "WHERE release_id = :release_id AND verification_status = 'TAMPERED'"
            ),
            {"release_id": str(release_id)},
        )
        row = result.first()
        return row.cnt == 0 if row else True