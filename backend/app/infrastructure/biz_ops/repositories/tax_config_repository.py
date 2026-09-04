"""TaxConfigRepository - 税务配置仓储。"""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.biz_ops.aggregates.tax_config_aggregate import (
    SpecialTaxRule,
    TaxConfigAggregate,
    TaxRateEntry,
)
from app.domain.biz_ops.enums.enums import TaxDirection, TaxFlag, TaxScopeLevel, TaxType
from app.domain.shared.entity import EntityId
from app.infrastructure.biz_ops.models import BizOpsTaxConfigORM


class TaxConfigRepository:
    """税务配置仓储。"""

    async def create(self, session: AsyncSession, agg: TaxConfigAggregate) -> BizOpsTaxConfigORM:
        orm = self._to_orm(agg)
        session.add(orm)
        await session.flush()
        return orm

    async def upsert(self, session: AsyncSession, agg: TaxConfigAggregate) -> BizOpsTaxConfigORM:
        existing = await self.get_by_key(session, agg.tenant_id, agg.config_key)
        if existing:
            existing.config_name = agg.config_name
            existing.tax_rates = self._rates_to_json(agg.tax_rates)
            existing.tax_flag = agg.tax_flag.value
            existing.direction = agg.direction.value
            existing.scope_level = agg.scope_level.value
            existing.scope_ref = agg.scope_ref
            existing.special_rules = self._rules_to_json(agg.special_rules)
            existing.is_active = "true" if agg.is_active else "false"
            existing.version = agg.version
            await session.flush()
            return existing
        return await self.create(session, agg)

    async def get_by_key(self, session: AsyncSession, tenant_id: UUID, config_key: str) -> BizOpsTaxConfigORM | None:
        stmt = select(BizOpsTaxConfigORM).where(
            BizOpsTaxConfigORM.tenant_id == tenant_id,
            BizOpsTaxConfigORM.config_key == config_key,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_tenant(self, session: AsyncSession, tenant_id: UUID) -> list[BizOpsTaxConfigORM]:
        stmt = select(BizOpsTaxConfigORM).where(BizOpsTaxConfigORM.tenant_id == tenant_id)
        return list((await session.execute(stmt)).scalars().all())

    def to_aggregate(self, orm: BizOpsTaxConfigORM) -> TaxConfigAggregate:
        return TaxConfigAggregate(
            id=EntityId(orm.id), tenant_id=orm.tenant_id, config_key=orm.config_key,
            config_name=orm.config_name, tax_rates=self._json_to_rates(orm.tax_rates),
            tax_flag=TaxFlag(orm.tax_flag), direction=TaxDirection(orm.direction),
            scope_level=TaxScopeLevel(orm.scope_level), scope_ref=orm.scope_ref,
            special_rules=self._json_to_rules(orm.special_rules),
            is_active=(orm.is_active == "true"), version=orm.version, description=orm.description,
        )

    def _to_orm(self, agg: TaxConfigAggregate) -> BizOpsTaxConfigORM:
        return BizOpsTaxConfigORM(
            id=agg.id.value, tenant_id=agg.tenant_id, config_key=agg.config_key,
            config_name=agg.config_name, tax_rates=self._rates_to_json(agg.tax_rates),
            tax_flag=agg.tax_flag.value, direction=agg.direction.value,
            scope_level=agg.scope_level.value, scope_ref=agg.scope_ref,
            special_rules=self._rules_to_json(agg.special_rules),
            is_active="true" if agg.is_active else "false", version=agg.version,
            description=agg.description,
        )

    def _rates_to_json(self, rates: tuple[TaxRateEntry, ...]) -> str:
        return json.dumps([
            {"tax_type": r.tax_type.value, "rate": r.rate, "is_default": r.is_default}
            for r in rates
        ], ensure_ascii=False)

    def _json_to_rates(self, raw: str) -> tuple[TaxRateEntry, ...]:
        data = json.loads(raw) if raw else []
        return tuple(
            TaxRateEntry(tax_type=TaxType(d["tax_type"]), rate=d["rate"], is_default=d.get("is_default", False))
            for d in data
        )

    def _rules_to_json(self, rules: tuple[SpecialTaxRule, ...]) -> str:
        return json.dumps([
            {"rule": r.rule, "description": r.description} for r in rules
        ], ensure_ascii=False)

    def _json_to_rules(self, raw: str) -> tuple[SpecialTaxRule, ...]:
        data = json.loads(raw) if raw else []
        return tuple(SpecialTaxRule(rule=d["rule"], description=d.get("description", "")) for d in data)