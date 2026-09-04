"""InventoryStrategyRepository - 库存策略仓储，版本化保存。"""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.biz_ops.aggregates.inventory_strategy_aggregate import InventoryStrategyAggregate
from app.domain.biz_ops.enums.enums import InvStrategyType, ScopeLevel
from app.domain.biz_ops.value_objects.inventory_strategy_config import InvActionConfig, InvThresholdConfig
from app.domain.shared.entity import EntityId
from app.infrastructure.biz_ops.models import (
    BizOpsInventoryStrategyORM,
    BizOpsInventoryStrategyVersionORM,
)


class InventoryStrategyRepository:
    """库存策略仓储 - 当前版本主表 + 历史版本副表。"""

    async def create(self, session: AsyncSession, agg: InventoryStrategyAggregate) -> BizOpsInventoryStrategyORM:
        orm = self._to_orm(agg)
        session.add(orm)
        await session.flush()
        ver_orm = self._to_version_orm(agg)
        session.add(ver_orm)
        await session.flush()
        return orm

    async def upsert(self, session: AsyncSession, agg: InventoryStrategyAggregate) -> BizOpsInventoryStrategyORM:
        existing = await self.get_by_key(session, agg.tenant_id, agg.strategy_key)
        if existing:
            ver_orm = self._to_version_orm(agg)
            session.add(ver_orm)
            existing.strategy_name = agg.strategy_name
            existing.threshold_config = self._threshold_to_json(agg.threshold_config)
            existing.action_config = self._action_to_json(agg.action_config)
            existing.scope_level = agg.scope_level.value
            existing.scope_ref = agg.scope_ref
            existing.priority = agg.priority
            existing.is_active = "true" if agg.is_active else "false"
            existing.version = agg.version
            await session.flush()
            return existing
        return await self.create(session, agg)

    async def get_by_key(self, session: AsyncSession, tenant_id: UUID, strategy_key: str) -> BizOpsInventoryStrategyORM | None:
        stmt = select(BizOpsInventoryStrategyORM).where(
            BizOpsInventoryStrategyORM.tenant_id == tenant_id,
            BizOpsInventoryStrategyORM.strategy_key == strategy_key,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_tenant(self, session: AsyncSession, tenant_id: UUID) -> list[BizOpsInventoryStrategyORM]:
        stmt = select(BizOpsInventoryStrategyORM).where(BizOpsInventoryStrategyORM.tenant_id == tenant_id)
        return list((await session.execute(stmt)).scalars().all())

    async def list_by_target(self, session: AsyncSession, tenant_id: UUID, target_ref: str) -> list[BizOpsInventoryStrategyORM]:
        stmt = select(BizOpsInventoryStrategyORM).where(
            BizOpsInventoryStrategyORM.tenant_id == tenant_id,
            BizOpsInventoryStrategyORM.target_ref == target_ref,
            BizOpsInventoryStrategyORM.is_active == "true",
        ).order_by(BizOpsInventoryStrategyORM.priority)
        return list((await session.execute(stmt)).scalars().all())

    def to_aggregate(self, orm: BizOpsInventoryStrategyORM) -> InventoryStrategyAggregate:
        return InventoryStrategyAggregate(
            id=EntityId(orm.id), tenant_id=orm.tenant_id, strategy_key=orm.strategy_key,
            strategy_name=orm.strategy_name, strategy_type=InvStrategyType(orm.strategy_type),
            target_ref=orm.target_ref,
            threshold_config=self._json_to_threshold(orm.threshold_config),
            action_config=self._json_to_action(orm.action_config),
            scope_level=ScopeLevel(orm.scope_level), scope_ref=orm.scope_ref,
            priority=orm.priority, is_active=(orm.is_active == "true"), version=orm.version,
            description=orm.description,
        )

    def _to_orm(self, agg: InventoryStrategyAggregate) -> BizOpsInventoryStrategyORM:
        return BizOpsInventoryStrategyORM(
            id=agg.id.value, tenant_id=agg.tenant_id, strategy_key=agg.strategy_key,
            strategy_name=agg.strategy_name, strategy_type=agg.strategy_type.value,
            target_ref=agg.target_ref,
            threshold_config=self._threshold_to_json(agg.threshold_config),
            action_config=self._action_to_json(agg.action_config),
            scope_level=agg.scope_level.value, scope_ref=agg.scope_ref,
            priority=agg.priority, is_active="true" if agg.is_active else "false",
            version=agg.version, description=agg.description,
        )

    def _to_version_orm(self, agg: InventoryStrategyAggregate) -> BizOpsInventoryStrategyVersionORM:
        return BizOpsInventoryStrategyVersionORM(
            id=EntityId.generate().value, tenant_id=agg.tenant_id, strategy_key=agg.strategy_key,
            strategy_name=agg.strategy_name, strategy_type=agg.strategy_type.value,
            target_ref=agg.target_ref,
            threshold_config=self._threshold_to_json(agg.threshold_config),
            action_config=self._action_to_json(agg.action_config),
            scope_level=agg.scope_level.value, scope_ref=agg.scope_ref,
            priority=agg.priority, version=agg.version, description=agg.description,
        )

    def _threshold_to_json(self, c: InvThresholdConfig) -> str:
        return json.dumps({
            "safety_stock": c.safety_stock, "min_stock": c.min_stock, "max_stock": c.max_stock,
            "reorder_point": c.reorder_point, "eoq": c.eoq, "alert_threshold": c.alert_threshold,
            "aging_days": c.aging_days, "abc_a_threshold": c.abc_a_threshold,
            "abc_b_threshold": c.abc_b_threshold, "periodic_days": c.periodic_days,
        }, ensure_ascii=False)

    def _json_to_threshold(self, raw: str) -> InvThresholdConfig:
        d = json.loads(raw) if raw else {}
        return InvThresholdConfig(
            safety_stock=d.get("safety_stock", 0), min_stock=d.get("min_stock", 0),
            max_stock=d.get("max_stock", 0), reorder_point=d.get("reorder_point", 0),
            eoq=d.get("eoq", 0), alert_threshold=d.get("alert_threshold", 0),
            aging_days=d.get("aging_days", 0), abc_a_threshold=d.get("abc_a_threshold", 0.8),
            abc_b_threshold=d.get("abc_b_threshold", 0.95), periodic_days=d.get("periodic_days", 0),
        )

    def _action_to_json(self, c: InvActionConfig) -> str:
        return json.dumps({
            "action_type": c.action_type,
            "notify_channels": list(c.notify_channels),
            "notify_recipients": list(c.notify_recipients),
            "auto_create_order": c.auto_create_order,
            "fifo_enforce": c.fifo_enforce,
            "expire_action": c.expire_action,
        }, ensure_ascii=False)

    def _json_to_action(self, raw: str) -> InvActionConfig:
        d = json.loads(raw) if raw else {}
        return InvActionConfig(
            action_type=d.get("action_type", "alert"),
            notify_channels=tuple(d.get("notify_channels", [])),
            notify_recipients=tuple(d.get("notify_recipients", [])),
            auto_create_order=d.get("auto_create_order", False),
            fifo_enforce=d.get("fifo_enforce", False),
            expire_action=d.get("expire_action", "warn"),
        )