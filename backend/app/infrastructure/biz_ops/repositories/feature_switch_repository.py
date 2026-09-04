"""FeatureSwitchRepository - 功能开关仓储，按 tenant_id 隔离查询。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.biz_ops.aggregates.feature_switch_aggregate import FeatureSwitchAggregate
from app.domain.biz_ops.enums.enums import FeatureScope
from app.domain.shared.entity import EntityId
from app.infrastructure.biz_ops.models import BizOpsFeatureSwitchORM


class FeatureSwitchRepository:
    """功能开关仓储 - 无状态，AsyncSession 方法参数注入。"""

    async def create(
        self, session: AsyncSession, agg: FeatureSwitchAggregate
    ) -> BizOpsFeatureSwitchORM:
        orm = BizOpsFeatureSwitchORM(
            id=agg.id.value,
            tenant_id=agg.tenant_id,
            feature_key=agg.feature_key,
            scope=agg.scope.value,
            is_enabled="true" if agg.is_enabled else "false",
            parent_feature_key=agg.parent_feature_key,
            description=agg.description,
            updated_by=agg.updated_by,
        )
        session.add(orm)
        await session.flush()
        return orm

    async def upsert(
        self, session: AsyncSession, agg: FeatureSwitchAggregate
    ) -> BizOpsFeatureSwitchORM:
        existing = await self.get_by_key(
            session, agg.tenant_id, agg.feature_key
        )
        if existing:
            existing.is_enabled = "true" if agg.is_enabled else "false"
            existing.updated_by = agg.updated_by
            await session.flush()
            return existing
        return await self.create(session, agg)

    async def get_by_key(
        self, session: AsyncSession, tenant_id: UUID, feature_key: str
    ) -> BizOpsFeatureSwitchORM | None:
        stmt = select(BizOpsFeatureSwitchORM).where(
            BizOpsFeatureSwitchORM.tenant_id == tenant_id,
            BizOpsFeatureSwitchORM.feature_key == feature_key,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self, session: AsyncSession, tenant_id: UUID
    ) -> list[BizOpsFeatureSwitchORM]:
        stmt = select(BizOpsFeatureSwitchORM).where(
            BizOpsFeatureSwitchORM.tenant_id == tenant_id
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def list_module_level(
        self, session: AsyncSession, tenant_id: UUID
    ) -> list[BizOpsFeatureSwitchORM]:
        stmt = select(BizOpsFeatureSwitchORM).where(
            BizOpsFeatureSwitchORM.tenant_id == tenant_id,
            BizOpsFeatureSwitchORM.scope == FeatureScope.MODULE.value,
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    def to_aggregate(self, orm: BizOpsFeatureSwitchORM) -> FeatureSwitchAggregate:
        """ORM → 聚合根转换。"""
        return FeatureSwitchAggregate(
            id=EntityId(orm.id),
            tenant_id=orm.tenant_id,
            feature_key=orm.feature_key,
            scope=FeatureScope(orm.scope),
            is_enabled=(orm.is_enabled == "true"),
            parent_feature_key=orm.parent_feature_key,
            description=orm.description,
            updated_by=orm.updated_by,
        )