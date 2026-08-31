"""WMS Task 仓储 - 作业任务查询与状态更新。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.warehouse.models import WmsTaskORM


class WmsTaskRepository:
    """WMS 作业任务仓储 - 状态机查询与幂等查重。"""

    async def get_by_id(
        self, session: AsyncSession, tenant_id: UUID, task_id: UUID
    ) -> WmsTaskORM | None:
        stmt = select(WmsTaskORM).where(
            WmsTaskORM.tenant_id == tenant_id,
            WmsTaskORM.task_id == task_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def get_by_idempotency_key(
        self, session: AsyncSession, tenant_id: UUID, idempotency_key: str
    ) -> WmsTaskORM | None:
        stmt = select(WmsTaskORM).where(
            WmsTaskORM.tenant_id == tenant_id,
            WmsTaskORM.idempotency_key == idempotency_key,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_status(
        self, session: AsyncSession, tenant_id: UUID, status: str, offset: int = 0, limit: int = 50
    ) -> list[WmsTaskORM]:
        stmt = (
            select(WmsTaskORM)
            .where(
                WmsTaskORM.tenant_id == tenant_id,
                WmsTaskORM.status == status,
            )
            .offset(offset)
            .limit(limit)
        )
        return list((await session.execute(stmt)).scalars().all())

    async def list_by_assignee(
        self, session: AsyncSession, tenant_id: UUID, assignee_id: UUID, status: str | None = None
    ) -> list[WmsTaskORM]:
        stmt = select(WmsTaskORM).where(
            WmsTaskORM.tenant_id == tenant_id,
            WmsTaskORM.assignee_id == assignee_id,
        )
        if status is not None:
            stmt = stmt.where(WmsTaskORM.status == status)
        return list((await session.execute(stmt)).scalars().all())

    async def list_by_document(
        self, session: AsyncSession, tenant_id: UUID, document_id: UUID
    ) -> list[WmsTaskORM]:
        stmt = select(WmsTaskORM).where(
            WmsTaskORM.tenant_id == tenant_id,
            WmsTaskORM.document_id == document_id,
        )
        return list((await session.execute(stmt)).scalars().all())

    async def list_pending_assignment(
        self, session: AsyncSession, tenant_id: UUID, offset: int = 0, limit: int = 50
    ) -> list[WmsTaskORM]:
        stmt = (
            select(WmsTaskORM)
            .where(
                WmsTaskORM.tenant_id == tenant_id,
                WmsTaskORM.status == "created",
            )
            .offset(offset)
            .limit(limit)
        )
        return list((await session.execute(stmt)).scalars().all())

    async def update_status(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        task_id: UUID,
        new_status: str,
        assigned_at: datetime | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        values: dict = {"status": new_status}
        if assigned_at is not None:
            values["assigned_at"] = assigned_at
        if started_at is not None:
            values["started_at"] = started_at
        if completed_at is not None:
            values["completed_at"] = completed_at
        stmt = (
            update(WmsTaskORM)
            .where(
                WmsTaskORM.tenant_id == tenant_id,
                WmsTaskORM.task_id == task_id,
            )
            .values(**values)
        )
        await session.execute(stmt)

    async def save(self, session: AsyncSession, orm: WmsTaskORM) -> WmsTaskORM:
        session.add(orm)
        await session.flush()
        return orm