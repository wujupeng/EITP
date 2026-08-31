"""WMS 审计与对账差异仓储 - append-only 审计 + 对账差异记录。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.warehouse.models import WmsOperationAuditORM, WmsReconcileDiffORM


class WmsOperationAuditRepository:
    """WMS 作业审计仓储 - append-only，仅 INSERT/SELECT。

    通过数据库层 REVOKE UPDATE/DELETE + Trigger 双保险确保不可变。
    """

    async def insert(self, session: AsyncSession, orm: WmsOperationAuditORM) -> WmsOperationAuditORM:
        session.add(orm)
        await session.flush()
        return orm

    async def get_by_id(
        self, session: AsyncSession, tenant_id: UUID, audit_id: UUID
    ) -> WmsOperationAuditORM | None:
        stmt = select(WmsOperationAuditORM).where(
            WmsOperationAuditORM.tenant_id == tenant_id,
            WmsOperationAuditORM.audit_id == audit_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_task(
        self, session: AsyncSession, tenant_id: UUID, task_id: UUID
    ) -> list[WmsOperationAuditORM]:
        stmt = select(WmsOperationAuditORM).where(
            WmsOperationAuditORM.tenant_id == tenant_id,
            WmsOperationAuditORM.task_id == task_id,
        )
        return list((await session.execute(stmt)).scalars().all())

    async def list_by_time_range(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        start: datetime,
        end: datetime,
        offset: int = 0,
        limit: int = 100,
    ) -> list[WmsOperationAuditORM]:
        stmt = (
            select(WmsOperationAuditORM)
            .where(
                WmsOperationAuditORM.tenant_id == tenant_id,
                WmsOperationAuditORM.operated_at >= start,
                WmsOperationAuditORM.operated_at < end,
            )
            .offset(offset)
            .limit(limit)
        )
        return list((await session.execute(stmt)).scalars().all())


class ReconcileDiffRepository:
    """对账差异仓储 - 记录 WMS 与 INV 的库存差异。"""

    async def save(self, session: AsyncSession, orm: WmsReconcileDiffORM) -> WmsReconcileDiffORM:
        session.add(orm)
        await session.flush()
        return orm

    async def get_by_id(
        self, session: AsyncSession, tenant_id: UUID, diff_id: UUID
    ) -> WmsReconcileDiffORM | None:
        stmt = select(WmsReconcileDiffORM).where(
            WmsReconcileDiffORM.tenant_id == tenant_id,
            WmsReconcileDiffORM.diff_id == diff_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_open_diffs(
        self, session: AsyncSession, tenant_id: UUID
    ) -> list[WmsReconcileDiffORM]:
        stmt = select(WmsReconcileDiffORM).where(
            WmsReconcileDiffORM.tenant_id == tenant_id,
            WmsReconcileDiffORM.status == "open",
        )
        return list((await session.execute(stmt)).scalars().all())

    async def list_by_sku_warehouse(
        self, session: AsyncSession, tenant_id: UUID, sku_id: UUID, warehouse_id: UUID
    ) -> list[WmsReconcileDiffORM]:
        stmt = select(WmsReconcileDiffORM).where(
            WmsReconcileDiffORM.tenant_id == tenant_id,
            WmsReconcileDiffORM.sku_id == sku_id,
            WmsReconcileDiffORM.warehouse_id == warehouse_id,
        )
        return list((await session.execute(stmt)).scalars().all())

    async def resolve(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        diff_id: UUID,
        resolution_note: str,
        resolved_at: datetime,
    ) -> None:
        stmt = select(WmsReconcileDiffORM).where(
            WmsReconcileDiffORM.tenant_id == tenant_id,
            WmsReconcileDiffORM.diff_id == diff_id,
        )
        orm = (await session.execute(stmt)).scalar_one_or_none()
        if orm is not None:
            orm.status = "resolved"
            orm.resolution_note = resolution_note
            orm.resolved_at = resolved_at
            await session.flush()