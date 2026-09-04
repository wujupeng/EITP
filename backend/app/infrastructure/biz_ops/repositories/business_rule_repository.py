"""BusinessRuleRepository - 业务规则仓储，版本化保存。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.biz_ops.aggregates.business_rule_aggregate import BusinessRuleAggregate
from app.domain.biz_ops.enums.enums import RuleAction, RuleType, ScopeLevel
from app.domain.shared.entity import EntityId
from app.infrastructure.biz_ops.models import (
    BizOpsBusinessRuleORM,
    BizOpsBusinessRuleVersionORM,
)


class BusinessRuleRepository:
    """业务规则仓储 - 当前版本主表 + 历史版本副表。"""

    async def create(self, session: AsyncSession, agg: BusinessRuleAggregate) -> BizOpsBusinessRuleORM:
        orm = self._to_orm(agg)
        session.add(orm)
        await session.flush()
        ver_orm = self._to_version_orm(agg)
        session.add(ver_orm)
        await session.flush()
        return orm

    async def upsert(self, session: AsyncSession, agg: BusinessRuleAggregate) -> BizOpsBusinessRuleORM:
        existing = await self.get_by_key(session, agg.tenant_id, agg.rule_key)
        if existing:
            ver_orm = self._to_version_orm(agg)
            session.add(ver_orm)
            existing.rule_name = agg.rule_name
            existing.expression = agg.expression
            existing.priority = agg.priority
            existing.is_active = "true" if agg.is_active else "false"
            existing.version = agg.version
            existing.action = agg.action.value if agg.action else None
            await session.flush()
            return existing
        return await self.create(session, agg)

    async def get_by_key(self, session: AsyncSession, tenant_id: UUID, rule_key: str) -> BizOpsBusinessRuleORM | None:
        stmt = select(BizOpsBusinessRuleORM).where(
            BizOpsBusinessRuleORM.tenant_id == tenant_id,
            BizOpsBusinessRuleORM.rule_key == rule_key,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_tenant(self, session: AsyncSession, tenant_id: UUID) -> list[BizOpsBusinessRuleORM]:
        stmt = select(BizOpsBusinessRuleORM).where(BizOpsBusinessRuleORM.tenant_id == tenant_id)
        return list((await session.execute(stmt)).scalars().all())

    async def list_by_trigger_point(self, session: AsyncSession, tenant_id: UUID, trigger_point: str) -> list[BizOpsBusinessRuleORM]:
        stmt = select(BizOpsBusinessRuleORM).where(
            BizOpsBusinessRuleORM.tenant_id == tenant_id,
            BizOpsBusinessRuleORM.trigger_point == trigger_point,
            BizOpsBusinessRuleORM.is_active == "true",
        )
        return list((await session.execute(stmt)).scalars().all())

    def to_aggregate(self, orm: BizOpsBusinessRuleORM) -> BusinessRuleAggregate:
        return BusinessRuleAggregate(
            id=EntityId(orm.id), tenant_id=orm.tenant_id, rule_key=orm.rule_key,
            rule_name=orm.rule_name, rule_type=RuleType(orm.rule_type),
            trigger_point=orm.trigger_point, expression=orm.expression,
            priority=orm.priority, scope_level=ScopeLevel(orm.scope_level),
            scope_ref=orm.scope_ref,
            action=RuleAction(orm.action) if orm.action else None,
            is_active=(orm.is_active == "true"), version=orm.version,
            description=orm.description, created_by=orm.created_by,
        )

    def _to_orm(self, agg: BusinessRuleAggregate) -> BizOpsBusinessRuleORM:
        return BizOpsBusinessRuleORM(
            id=agg.id.value, tenant_id=agg.tenant_id, rule_key=agg.rule_key,
            rule_name=agg.rule_name, rule_type=agg.rule_type.value,
            trigger_point=agg.trigger_point, expression=agg.expression,
            priority=agg.priority, scope_level=agg.scope_level.value,
            scope_ref=agg.scope_ref,
            action=agg.action.value if agg.action else None,
            is_active="true" if agg.is_active else "false",
            version=agg.version, description=agg.description, created_by=agg.created_by,
        )

    def _to_version_orm(self, agg: BusinessRuleAggregate) -> BizOpsBusinessRuleVersionORM:
        return BizOpsBusinessRuleVersionORM(
            id=EntityId.generate().value, tenant_id=agg.tenant_id, rule_key=agg.rule_key,
            rule_name=agg.rule_name, rule_type=agg.rule_type.value,
            trigger_point=agg.trigger_point, expression=agg.expression,
            priority=agg.priority, scope_level=agg.scope_level.value,
            scope_ref=agg.scope_ref,
            action=agg.action.value if agg.action else None,
            version=agg.version, description=agg.description, created_by=agg.created_by,
        )