"""GroupReportAppSvc - 集团报表应用服务，编排聚合根与仓储。"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.group.group_aggregate import GroupAggregate, PropagateResult
from app.domain.group.readonly_boundary import (
    GroupActor,
    OperationType,
    ReadonlyBoundary,
    SubsidiaryIsolationGuard,
)
from app.domain.group.summary_snapshot import ReportDimension, SummarySnapshot
from app.domain.shared.entity import EntityId
from app.infrastructure.group.repository import GroupRepository
from app.interfaces.middleware.tenant_context import TenantContext


class GroupReportAppSvc:
    """集团报表应用服务 - 跨公司汇总查询与主数据下发。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = GroupRepository(session)

    async def get_group_report(
        self,
        enterprise_id: UUID,
        dimension: ReportDimension,
        organization_ids: tuple[UUID, ...] | None = None,
    ) -> tuple[dict, bool, int]:
        """查询集团汇总报表。

        Returns:
            (汇总值, is_delayed, 组织数)
        """
        snapshots = await self._repo.get_snapshots_by_enterprise(
            enterprise_id, dimension
        )

        aggregate = GroupAggregate(EntityId.generate(), enterprise_id)
        for snapshot in snapshots:
            aggregate.update_snapshot(snapshot)

        return aggregate.aggregate_report(
            dimension, organization_ids, datetime.now(timezone.utc)
        )

    async def enforce_readonly_boundary(
        self,
        actor: GroupActor,
        operation: OperationType,
        target_organization_id: UUID,
    ) -> None:
        """强制集团只读边界。"""
        ReadonlyBoundary.enforce(actor, operation, target_organization_id)

    async def enforce_subsidiary_isolation(
        self,
        actor_org_id: UUID,
        requested_org_id: UUID,
        enterprise_id: UUID,
    ) -> None:
        """强制子公司管理员隔离。"""
        SubsidiaryIsolationGuard.enforce(
            actor_org_id, requested_org_id, enterprise_id
        )

    async def update_snapshot(
        self,
        enterprise_id: UUID,
        organization_id: UUID,
        dimension: ReportDimension,
        snapshot_value: dict,
        source_version: int = 0,
    ) -> SummarySnapshot:
        """更新汇总快照（由异步消费者调用）。"""
        snapshot = SummarySnapshot.create(
            enterprise_id=enterprise_id,
            organization_id=organization_id,
            dimension=dimension,
            snapshot_value=snapshot_value,
            source_version=source_version,
        )
        await self._repo.upsert_snapshot(snapshot)
        await self._session.commit()
        return snapshot

    async def propagate_master_data(
        self,
        enterprise_id: UUID,
        master_data_type: str,
        master_data_id: str,
        target_org_ids: tuple[UUID, ...],
        existing_codes: dict[UUID, set[str]] | None = None,
    ) -> PropagateResult:
        """集团主数据下发至子公司。"""
        aggregate = GroupAggregate(EntityId.generate(), enterprise_id)
        for org_id in target_org_ids:
            aggregate.add_organization(org_id)

        result = aggregate.propagate_master_data(
            master_data_type=master_data_type,
            master_data_id=master_data_id,
            target_org_ids=target_org_ids,
            existing_codes=existing_codes,
        )
        await self._session.commit()
        return result