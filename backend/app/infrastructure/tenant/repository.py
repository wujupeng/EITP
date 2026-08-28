"""TenantRepository - 租户持久化与幂等键校验。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.shared.entity import EntityId
from app.domain.tenant.tenant_aggregate import TenantAggregate
from app.domain.tenant.tenant_state import DataPlacement, TenantStatus
from app.infrastructure.tenant.models import TenantORM


class TenantRepository:
    """租户仓储 - 平台级操作，不受租户隔离过滤影响。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, tenant_id: UUID) -> TenantAggregate | None:
        stmt = select(TenantORM).where(TenantORM.id == tenant_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return self._to_domain(orm)

    async def get_by_idempotency_key(self, key: str) -> TenantAggregate | None:
        """按幂等键查询 - 用于开通幂等控制。"""
        stmt = select(TenantORM).where(TenantORM.idempotency_key == key)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return self._to_domain(orm)

    async def save(self, tenant: TenantAggregate) -> TenantAggregate:
        orm = TenantORM(
            id=tenant.id.value,
            enterprise_name=tenant.enterprise_name,
            status=tenant.status.value,
            data_placement=tenant.data_placement.value,
            version=tenant.version,
            idempotency_key=tenant.idempotency_key,
        )
        self._session.add(orm)
        await self._session.flush()
        return tenant

    async def update_status(
        self,
        tenant_id: UUID,
        status: TenantStatus,
    ) -> None:
        from sqlalchemy import update
        stmt = (
            update(TenantORM)
            .where(TenantORM.id == tenant_id)
            .values(status=status.value, updated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc))
        )
        await self._session.execute(stmt)

    async def list_all(self, offset: int = 0, limit: int = 50) -> list[TenantAggregate]:
        stmt = (
            select(TenantORM)
            .order_by(TenantORM.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars()]

    @staticmethod
    def _to_domain(orm: TenantORM) -> TenantAggregate:
        return TenantAggregate(
            id=EntityId(orm.id),
            enterprise_name=orm.enterprise_name,
            idempotency_key=orm.idempotency_key or "",
            status=TenantStatus(orm.status),
            data_placement=DataPlacement(orm.data_placement),
            version=orm.version,
        )