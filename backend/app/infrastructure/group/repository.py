"""集团报表仓储 - SummarySnapshot 持久化与查询。"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.group.summary_snapshot import ReportDimension, SummarySnapshot
from app.infrastructure.group.models import SummarySnapshotORM


class GroupRepository:
    """集团报表仓储 - SummarySnapshot upsert 与查询。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_snapshot(self, snapshot: SummarySnapshot) -> None:
        """upsert 汇总快照（按 enterprise+org+dimension 唯一键）。"""
        stmt = pg_insert(SummarySnapshotORM).values(
            snapshot_id=snapshot.snapshot_id,
            enterprise_id=snapshot.enterprise_id,
            organization_id=snapshot.organization_id,
            dimension=snapshot.dimension.value,
            snapshot_value=snapshot.snapshot_value,
            snapshot_at=snapshot.snapshot_at,
            source_version=snapshot.source_version,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["enterprise_id", "organization_id", "dimension"],
            set_={
                "snapshot_value": stmt.excluded.snapshot_value,
                "snapshot_at": stmt.excluded.snapshot_at,
                "source_version": stmt.excluded.source_version,
            },
        )
        await self._session.execute(stmt)

    async def get_snapshot(
        self,
        enterprise_id: UUID,
        organization_id: UUID,
        dimension: ReportDimension,
    ) -> SummarySnapshot | None:
        """查询单个快照。"""
        stmt = select(SummarySnapshotORM).where(
            SummarySnapshotORM.enterprise_id == enterprise_id,
            SummarySnapshotORM.organization_id == organization_id,
            SummarySnapshotORM.dimension == dimension.value,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return SummarySnapshot(
            snapshot_id=orm.snapshot_id,
            enterprise_id=orm.enterprise_id,
            organization_id=orm.organization_id,
            dimension=ReportDimension(orm.dimension),
            snapshot_value=orm.snapshot_value,
            snapshot_at=orm.snapshot_at,
            source_version=orm.source_version,
        )

    async def get_snapshots_by_enterprise(
        self,
        enterprise_id: UUID,
        dimension: ReportDimension,
    ) -> list[SummarySnapshot]:
        """查询 Enterprise 下所有子公司的指定维度快照。"""
        stmt = select(SummarySnapshotORM).where(
            SummarySnapshotORM.enterprise_id == enterprise_id,
            SummarySnapshotORM.dimension == dimension.value,
        )
        result = await self._session.execute(stmt)
        return [
            SummarySnapshot(
                snapshot_id=orm.snapshot_id,
                enterprise_id=orm.enterprise_id,
                organization_id=orm.organization_id,
                dimension=ReportDimension(orm.dimension),
                snapshot_value=orm.snapshot_value,
                snapshot_at=orm.snapshot_at,
                source_version=orm.source_version,
            )
            for orm in result.scalars()
        ]