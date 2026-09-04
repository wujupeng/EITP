"""PricingStrategyRepository - 定价策略仓储，版本化保存。"""

from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.biz_ops.aggregates.pricing_strategy_aggregate import PricingStrategyAggregate
from app.domain.biz_ops.enums.enums import PricingType, ScopeLevel
from app.domain.biz_ops.value_objects.price_config import PriceConfig, TierPrice
from app.domain.shared.entity import EntityId
from app.infrastructure.biz_ops.models import (
    BizOpsPricingStrategyORM,
    BizOpsPricingStrategyVersionORM,
)


class PricingStrategyRepository:
    """定价策略仓储 - 当前版本主表 + 历史版本副表。"""

    async def create(self, session: AsyncSession, agg: PricingStrategyAggregate) -> BizOpsPricingStrategyORM:
        orm = self._to_orm(agg)
        session.add(orm)
        await session.flush()
        ver_orm = self._to_version_orm(agg)
        session.add(ver_orm)
        await session.flush()
        return orm

    async def upsert(self, session: AsyncSession, agg: PricingStrategyAggregate) -> BizOpsPricingStrategyORM:
        existing = await self.get_by_key(session, agg.tenant_id, agg.strategy_key)
        if existing:
            ver_orm = self._to_version_orm(agg)
            session.add(ver_orm)
            existing.strategy_name = agg.strategy_name
            existing.target_ref = agg.target_ref
            existing.price_config = self._config_to_json(agg.price_config)
            existing.scope_level = agg.scope_level.value
            existing.scope_ref = agg.scope_ref
            existing.priority = agg.priority
            existing.effective_from = agg.effective_from
            existing.effective_to = agg.effective_to
            existing.is_active = "true" if agg.is_active else "false"
            existing.version = agg.version
            await session.flush()
            return existing
        return await self.create(session, agg)

    async def get_by_key(self, session: AsyncSession, tenant_id: UUID, strategy_key: str) -> BizOpsPricingStrategyORM | None:
        stmt = select(BizOpsPricingStrategyORM).where(
            BizOpsPricingStrategyORM.tenant_id == tenant_id,
            BizOpsPricingStrategyORM.strategy_key == strategy_key,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def get_by_id(self, session: AsyncSession, tenant_id: UUID, strategy_id: UUID) -> BizOpsPricingStrategyORM | None:
        stmt = select(BizOpsPricingStrategyORM).where(
            BizOpsPricingStrategyORM.tenant_id == tenant_id,
            BizOpsPricingStrategyORM.id == strategy_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_tenant(self, session: AsyncSession, tenant_id: UUID) -> list[BizOpsPricingStrategyORM]:
        stmt = select(BizOpsPricingStrategyORM).where(BizOpsPricingStrategyORM.tenant_id == tenant_id)
        return list((await session.execute(stmt)).scalars().all())

    async def list_by_type(
        self, session: AsyncSession, tenant_id: UUID, strategy_type: str
    ) -> list[BizOpsPricingStrategyORM]:
        stmt = select(BizOpsPricingStrategyORM).where(
            BizOpsPricingStrategyORM.tenant_id == tenant_id,
            BizOpsPricingStrategyORM.strategy_type == strategy_type,
            BizOpsPricingStrategyORM.is_active == "true",
        )
        return list((await session.execute(stmt)).scalars().all())

    async def list_by_target(
        self, session: AsyncSession, tenant_id: UUID, target_ref: str
    ) -> list[BizOpsPricingStrategyORM]:
        stmt = select(BizOpsPricingStrategyORM).where(
            BizOpsPricingStrategyORM.tenant_id == tenant_id,
            BizOpsPricingStrategyORM.target_ref == target_ref,
            BizOpsPricingStrategyORM.is_active == "true",
        ).order_by(BizOpsPricingStrategyORM.priority)
        return list((await session.execute(stmt)).scalars().all())

    def to_aggregate(self, orm: BizOpsPricingStrategyORM) -> PricingStrategyAggregate:
        return PricingStrategyAggregate(
            id=EntityId(orm.id), tenant_id=orm.tenant_id, strategy_key=orm.strategy_key,
            strategy_name=orm.strategy_name, strategy_type=PricingType(orm.strategy_type),
            target_ref=orm.target_ref, price_config=self._json_to_config(orm.price_config),
            scope_level=ScopeLevel(orm.scope_level), scope_ref=orm.scope_ref,
            priority=orm.priority, effective_from=orm.effective_from, effective_to=orm.effective_to,
            is_active=(orm.is_active == "true"), version=orm.version,
        )

    def _to_orm(self, agg: PricingStrategyAggregate) -> BizOpsPricingStrategyORM:
        return BizOpsPricingStrategyORM(
            id=agg.id.value, tenant_id=agg.tenant_id, strategy_key=agg.strategy_key,
            strategy_name=agg.strategy_name, strategy_type=agg.strategy_type.value,
            target_ref=agg.target_ref, price_config=self._config_to_json(agg.price_config),
            scope_level=agg.scope_level.value, scope_ref=agg.scope_ref,
            priority=agg.priority, effective_from=agg.effective_from, effective_to=agg.effective_to,
            is_active="true" if agg.is_active else "false", version=agg.version,
        )

    def _to_version_orm(self, agg: PricingStrategyAggregate) -> BizOpsPricingStrategyVersionORM:
        return BizOpsPricingStrategyVersionORM(
            id=EntityId.generate().value, tenant_id=agg.tenant_id, strategy_key=agg.strategy_key,
            strategy_name=agg.strategy_name, strategy_type=agg.strategy_type.value,
            target_ref=agg.target_ref, price_config=self._config_to_json(agg.price_config),
            scope_level=agg.scope_level.value, scope_ref=agg.scope_ref,
            priority=agg.priority, effective_from=agg.effective_from, effective_to=agg.effective_to,
            version=agg.version,
        )

    def _config_to_json(self, config: PriceConfig) -> str:
        return json.dumps({
            "base_price": config.base_price,
            "discount_rate": config.discount_rate,
            "markup_rate": config.markup_rate,
            "tier_prices": [
                {"min_quantity": t.min_quantity, "max_quantity": t.max_quantity, "unit_price": t.unit_price}
                for t in config.tier_prices
            ],
        }, ensure_ascii=False)

    def _json_to_config(self, raw: str) -> PriceConfig:
        data = json.loads(raw) if raw else {}
        tiers = tuple(
            TierPrice(min_quantity=t["min_quantity"], max_quantity=t["max_quantity"], unit_price=t["unit_price"])
            for t in data.get("tier_prices", [])
        )
        return PriceConfig(
            base_price=data.get("base_price", 0.0),
            discount_rate=data.get("discount_rate", 0.0),
            markup_rate=data.get("markup_rate", 0.0),
            tier_prices=tiers,
        )