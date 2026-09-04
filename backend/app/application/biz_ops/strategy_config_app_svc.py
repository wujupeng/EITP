"""StrategyConfigAppSvc - 策略配置应用服务（业务规则 + 定价 + 税务 + 库存策略配置编排）。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.biz_ops.aggregates.business_rule_aggregate import BusinessRuleAggregate
from app.domain.biz_ops.aggregates.inventory_strategy_aggregate import InventoryStrategyAggregate
from app.domain.biz_ops.aggregates.pricing_strategy_aggregate import PricingStrategyAggregate
from app.domain.biz_ops.aggregates.tax_config_aggregate import (
    SpecialTaxRule,
    TaxConfigAggregate,
    TaxRateEntry,
)
from app.domain.biz_ops.enums.enums import (
    InvStrategyType,
    PricingType,
    RuleAction,
    RuleType,
    ScopeLevel,
    TaxDirection,
    TaxFlag,
    TaxScopeLevel,
    TaxType,
)
from app.domain.biz_ops.services.tax_engine import TaxEngine
from app.domain.biz_ops.value_objects.inventory_strategy_config import InvActionConfig, InvThresholdConfig
from app.domain.biz_ops.value_objects.price_config import PriceConfig, TierPrice
from app.domain.shared.entity import EntityId
from app.infrastructure.biz_ops.repositories.business_rule_repository import BusinessRuleRepository
from app.infrastructure.biz_ops.repositories.inventory_strategy_repository import InventoryStrategyRepository
from app.infrastructure.biz_ops.repositories.pricing_strategy_repository import PricingStrategyRepository
from app.infrastructure.biz_ops.repositories.tax_config_repository import TaxConfigRepository
from app.interfaces.middleware.error_handler import BizOpsError, BizOpsErrorCode


class StrategyConfigAppSvc:
    """策略配置应用服务 - 业务规则 + 定价 + 税务 + 库存策略配置编排。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._rule_repo = BusinessRuleRepository()
        self._pricing_repo = PricingStrategyRepository()
        self._tax_repo = TaxConfigRepository()
        self._inv_repo = InventoryStrategyRepository()
        self._tax_engine = TaxEngine()

    async def create_rule(self, tenant_id: UUID, created_by: UUID, req: dict) -> dict:
        existing = await self._rule_repo.get_by_key(self._session, tenant_id, req["rule_key"])
        if existing:
            raise BizOpsError(BizOpsErrorCode.RULE_KEY_DUPLICATE, f"规则键已存在: {req['rule_key']}")
        agg = BusinessRuleAggregate(
            id=EntityId.generate(), tenant_id=tenant_id, rule_key=req["rule_key"],
            rule_name=req["rule_name"], rule_type=RuleType(req["rule_type"]),
            trigger_point=req["trigger_point"], expression=req["expression"],
            priority=req.get("priority", 100), scope_level=ScopeLevel(req.get("scope_level", "tenant")),
            scope_ref=req.get("scope_ref"),
            action=RuleAction(req["action"]) if req.get("action") else None,
            description=req.get("description"), created_by=created_by,
        )
        orm = await self._rule_repo.create(self._session, agg)
        await self._session.commit()
        return {"id": str(orm.id), "rule_key": orm.rule_key, "version": orm.version}

    async def list_rules(self, tenant_id: UUID) -> list[dict]:
        orm_list = await self._rule_repo.list_by_tenant(self._session, tenant_id)
        return [{"id": str(o.id), "rule_key": o.rule_key, "rule_name": o.rule_name,
                 "rule_type": o.rule_type, "is_active": o.is_active == "true", "version": o.version} for o in orm_list]

    async def update_rule(self, tenant_id: UUID, rule_key: str, req: dict) -> dict:
        orm = await self._rule_repo.get_by_key(self._session, tenant_id, rule_key)
        if orm is None:
            raise BizOpsError(BizOpsErrorCode.RULE_NOT_FOUND, f"规则不存在: {rule_key}")
        agg = self._rule_repo.to_aggregate(orm)
        if "expression" in req and req["expression"]:
            agg = agg.update_expression(req["expression"])
        if "rule_name" in req and req["rule_name"]:
            agg = BusinessRuleAggregate(
                id=agg.id, tenant_id=agg.tenant_id, rule_key=agg.rule_key,
                rule_name=req["rule_name"], rule_type=agg.rule_type,
                trigger_point=agg.trigger_point, expression=agg.expression,
                priority=req.get("priority", agg.priority), scope_level=agg.scope_level,
                scope_ref=agg.scope_ref, action=agg.action, is_active=agg.is_active,
                version=agg.version, description=req.get("description", agg.description), created_by=agg.created_by,
            )
        updated = await self._rule_repo.upsert(self._session, agg)
        await self._session.commit()
        return {"id": str(updated.id), "rule_key": updated.rule_key, "version": updated.version}

    async def activate_rule(self, tenant_id: UUID, rule_key: str) -> dict:
        orm = await self._rule_repo.get_by_key(self._session, tenant_id, rule_key)
        if orm is None:
            raise BizOpsError(BizOpsErrorCode.RULE_NOT_FOUND, f"规则不存在: {rule_key}")
        agg = self._rule_repo.to_aggregate(orm).activate()
        await self._rule_repo.upsert(self._session, agg)
        await self._session.commit()
        return {"rule_key": rule_key, "is_active": True}

    async def deactivate_rule(self, tenant_id: UUID, rule_key: str) -> dict:
        orm = await self._rule_repo.get_by_key(self._session, tenant_id, rule_key)
        if orm is None:
            raise BizOpsError(BizOpsErrorCode.RULE_NOT_FOUND, f"规则不存在: {rule_key}")
        agg = self._rule_repo.to_aggregate(orm).deactivate()
        await self._rule_repo.upsert(self._session, agg)
        await self._session.commit()
        return {"rule_key": rule_key, "is_active": False}

    # ==================== 定价策略配置 ====================

    async def create_pricing_strategy(self, tenant_id: UUID, created_by: UUID, req: dict) -> dict:
        existing = await self._pricing_repo.get_by_key(self._session, tenant_id, req["strategy_key"])
        if existing:
            raise BizOpsError(BizOpsErrorCode.PRICING_CALCULATION_FAILED, f"策略键已存在: {req['strategy_key']}")
        agg = PricingStrategyAggregate(
            id=EntityId.generate(), tenant_id=tenant_id, strategy_key=req["strategy_key"],
            strategy_name=req["strategy_name"], strategy_type=PricingType(req["strategy_type"]),
            target_ref=req["target_ref"], price_config=self._dict_to_config(req["price_config"]),
            scope_level=ScopeLevel(req.get("scope_level", "tenant")), scope_ref=req.get("scope_ref"),
            priority=req.get("priority", 100),
            effective_from=req.get("effective_from"), effective_to=req.get("effective_to"),
        )
        orm = await self._pricing_repo.create(self._session, agg)
        await self._session.commit()
        return {"id": str(orm.id), "strategy_key": orm.strategy_key, "version": orm.version}

    async def list_pricing_strategies(self, tenant_id: UUID) -> list[dict]:
        orm_list = await self._pricing_repo.list_by_tenant(self._session, tenant_id)
        return [self._pricing_orm_to_dict(o) for o in orm_list]

    async def get_pricing_strategy(self, tenant_id: UUID, strategy_key: str) -> dict:
        orm = await self._pricing_repo.get_by_key(self._session, tenant_id, strategy_key)
        if orm is None:
            raise BizOpsError(BizOpsErrorCode.PRICING_CALCULATION_FAILED, f"策略不存在: {strategy_key}")
        return self._pricing_orm_to_dict(orm)

    async def update_pricing_strategy(self, tenant_id: UUID, strategy_key: str, req: dict) -> dict:
        orm = await self._pricing_repo.get_by_key(self._session, tenant_id, strategy_key)
        if orm is None:
            raise BizOpsError(BizOpsErrorCode.PRICING_CALCULATION_FAILED, f"策略不存在: {strategy_key}")
        agg = self._pricing_repo.to_aggregate(orm)
        new_config = self._dict_to_config(req["price_config"]) if req.get("price_config") else agg.price_config
        new_agg = PricingStrategyAggregate(
            id=agg.id, tenant_id=agg.tenant_id, strategy_key=agg.strategy_key,
            strategy_name=req.get("strategy_name", agg.strategy_name), strategy_type=agg.strategy_type,
            target_ref=agg.target_ref, price_config=new_config,
            scope_level=agg.scope_level, scope_ref=agg.scope_ref,
            priority=req.get("priority", agg.priority),
            effective_from=req.get("effective_from", agg.effective_from),
            effective_to=req.get("effective_to", agg.effective_to),
            is_active=req.get("is_active", agg.is_active), version=agg.version + 1,
        )
        updated = await self._pricing_repo.upsert(self._session, new_agg)
        await self._session.commit()
        return {"id": str(updated.id), "strategy_key": updated.strategy_key, "version": updated.version}

    def _dict_to_config(self, d: dict) -> PriceConfig:
        tiers = tuple(
            TierPrice(min_quantity=t["min_quantity"], max_quantity=t["max_quantity"], unit_price=t["unit_price"])
            for t in d.get("tier_prices", [])
        )
        return PriceConfig(
            base_price=d.get("base_price", 0.0),
            discount_rate=d.get("discount_rate", 0.0),
            markup_rate=d.get("markup_rate", 0.0),
            tier_prices=tiers,
        )

    def _pricing_orm_to_dict(self, orm) -> dict:
        agg = self._pricing_repo.to_aggregate(orm)
        return {
            "id": str(orm.id), "tenant_id": str(orm.tenant_id),
            "strategy_key": orm.strategy_key, "strategy_name": orm.strategy_name,
            "strategy_type": orm.strategy_type, "target_ref": orm.target_ref,
            "price_config": {
                "base_price": agg.price_config.base_price,
                "discount_rate": agg.price_config.discount_rate,
                "markup_rate": agg.price_config.markup_rate,
                "tier_prices": [
                    {"min_quantity": t.min_quantity, "max_quantity": t.max_quantity, "unit_price": t.unit_price}
                    for t in agg.price_config.tier_prices
                ],
            },
            "scope_level": orm.scope_level, "scope_ref": orm.scope_ref,
            "priority": orm.priority, "effective_from": orm.effective_from, "effective_to": orm.effective_to,
            "is_active": orm.is_active == "true", "version": orm.version,
        }

    # ==================== 税务配置 ====================

    async def create_tax_config(self, tenant_id: UUID, req: dict) -> dict:
        existing = await self._tax_repo.get_by_key(self._session, tenant_id, req["config_key"])
        if existing:
            raise BizOpsError(BizOpsErrorCode.TAX_CALCULATION_FAILED, f"配置键已存在: {req['config_key']}")
        agg = TaxConfigAggregate(
            id=EntityId.generate(), tenant_id=tenant_id, config_key=req["config_key"],
            config_name=req["config_name"], tax_rates=self._dict_to_rates(req["tax_rates"]),
            tax_flag=TaxFlag(req.get("tax_flag", "tax_exclusive")),
            direction=TaxDirection(req.get("direction", "output")),
            scope_level=TaxScopeLevel(req.get("scope_level", "tenant")), scope_ref=req.get("scope_ref"),
            special_rules=self._dict_to_rules(req.get("special_rules", [])),
            description=req.get("description"),
        )
        orm = await self._tax_repo.create(self._session, agg)
        await self._session.commit()
        return {"id": str(orm.id), "config_key": orm.config_key, "version": orm.version}

    async def list_tax_configs(self, tenant_id: UUID) -> list[dict]:
        orm_list = await self._tax_repo.list_by_tenant(self._session, tenant_id)
        return [self._tax_orm_to_dict(o) for o in orm_list]

    async def update_tax_config(self, tenant_id: UUID, config_key: str, req: dict) -> dict:
        orm = await self._tax_repo.get_by_key(self._session, tenant_id, config_key)
        if orm is None:
            raise BizOpsError(BizOpsErrorCode.TAX_CALCULATION_FAILED, f"配置不存在: {config_key}")
        agg = self._tax_repo.to_aggregate(orm)
        new_agg = TaxConfigAggregate(
            id=agg.id, tenant_id=agg.tenant_id, config_key=agg.config_key,
            config_name=req.get("config_name", agg.config_name),
            tax_rates=self._dict_to_rates(req["tax_rates"]) if req.get("tax_rates") else agg.tax_rates,
            tax_flag=TaxFlag(req["tax_flag"]) if req.get("tax_flag") else agg.tax_flag,
            direction=TaxDirection(req["direction"]) if req.get("direction") else agg.direction,
            scope_level=agg.scope_level, scope_ref=agg.scope_ref,
            special_rules=agg.special_rules,
            is_active=req.get("is_active", agg.is_active), version=agg.version + 1,
            description=req.get("description", agg.description),
        )
        updated = await self._tax_repo.upsert(self._session, new_agg)
        await self._session.commit()
        return {"id": str(updated.id), "config_key": updated.config_key, "version": updated.version}

    async def calculate_tax(self, tenant_id: UUID, req: dict) -> dict:
        orm = await self._tax_repo.get_by_key(self._session, tenant_id, req["config_key"])
        if orm is None:
            raise BizOpsError(BizOpsErrorCode.TAX_CALCULATION_FAILED, f"配置不存在: {req['config_key']}")
        agg = self._tax_repo.to_aggregate(orm)
        result = self._tax_engine.calculate(agg, req["lines"])
        return {
            "config_id": str(result.config_id), "config_key": result.config_key,
            "lines": [
                {"line_id": l.line_id, "tax_type": l.tax_type.value, "direction": l.direction.value,
                 "tax_flag": l.tax_flag.value, "base_amount": l.base_amount,
                 "tax_amount": l.tax_amount, "total_amount": l.total_amount}
                for l in result.lines
            ],
            "total_tax": result.total_tax, "total_amount": result.total_amount,
        }

    def _dict_to_rates(self, rates: list[dict]) -> tuple[TaxRateEntry, ...]:
        return tuple(
            TaxRateEntry(tax_type=TaxType(r["tax_type"]), rate=r["rate"], is_default=r.get("is_default", False))
            for r in rates
        )

    def _dict_to_rules(self, rules: list[dict]) -> tuple[SpecialTaxRule, ...]:
        return tuple(SpecialTaxRule(rule=r["rule"], description=r.get("description", "")) for r in rules)

    def _tax_orm_to_dict(self, orm) -> dict:
        agg = self._tax_repo.to_aggregate(orm)
        return {
            "id": str(orm.id), "tenant_id": str(orm.tenant_id),
            "config_key": orm.config_key, "config_name": orm.config_name,
            "tax_rates": [
                {"tax_type": r.tax_type.value, "rate": r.rate, "is_default": r.is_default}
                for r in agg.tax_rates
            ],
            "tax_flag": orm.tax_flag, "direction": orm.direction,
            "scope_level": orm.scope_level, "scope_ref": orm.scope_ref,
            "special_rules": [
                {"rule": r.rule, "description": r.description} for r in agg.special_rules
            ],
            "is_active": orm.is_active == "true", "version": orm.version,
        }

    # ==================== 库存策略配置 ====================

    async def create_inventory_strategy(self, tenant_id: UUID, req: dict) -> dict:
        agg = InventoryStrategyAggregate(
            id=EntityId.generate(), tenant_id=tenant_id, strategy_key=req["strategy_key"],
            strategy_name=req["strategy_name"], strategy_type=InvStrategyType(req["strategy_type"]),
            target_ref=req["target_ref"],
            threshold_config=self._dict_to_threshold(req["threshold_config"]),
            action_config=self._dict_to_action(req.get("action_config", {})),
            scope_level=ScopeLevel(req.get("scope_level", "tenant")), scope_ref=req.get("scope_ref"),
            priority=req.get("priority", 100), description=req.get("description"),
        )
        orm = await self._inv_repo.create(self._session, agg)
        await self._session.commit()
        return {"id": str(orm.id), "strategy_key": orm.strategy_key, "version": orm.version}

    async def list_inventory_strategies(self, tenant_id: UUID) -> list[dict]:
        orm_list = await self._inv_repo.list_by_tenant(self._session, tenant_id)
        return [self._inv_orm_to_dict(o) for o in orm_list]

    async def update_inventory_strategy(self, tenant_id: UUID, strategy_key: str, req: dict) -> dict:
        orm = await self._inv_repo.get_by_key(self._session, tenant_id, strategy_key)
        if orm is None:
            raise BizOpsError(BizOpsErrorCode.INV_STRATEGY_CHECK_FAILED, f"策略不存在: {strategy_key}")
        agg = self._inv_repo.to_aggregate(orm)
        new_agg = InventoryStrategyAggregate(
            id=agg.id, tenant_id=agg.tenant_id, strategy_key=agg.strategy_key,
            strategy_name=req.get("strategy_name", agg.strategy_name), strategy_type=agg.strategy_type,
            target_ref=agg.target_ref,
            threshold_config=self._dict_to_threshold(req["threshold_config"]) if req.get("threshold_config") else agg.threshold_config,
            action_config=self._dict_to_action(req["action_config"]) if req.get("action_config") else agg.action_config,
            scope_level=agg.scope_level, scope_ref=agg.scope_ref,
            priority=req.get("priority", agg.priority),
            is_active=req.get("is_active", agg.is_active), version=agg.version + 1,
            description=req.get("description", agg.description),
        )
        updated = await self._inv_repo.upsert(self._session, new_agg)
        await self._session.commit()
        return {"id": str(updated.id), "strategy_key": updated.strategy_key, "version": updated.version}

    def _dict_to_threshold(self, d: dict) -> InvThresholdConfig:
        return InvThresholdConfig(
            safety_stock=d.get("safety_stock", 0), min_stock=d.get("min_stock", 0),
            max_stock=d.get("max_stock", 0), reorder_point=d.get("reorder_point", 0),
            eoq=d.get("eoq", 0), alert_threshold=d.get("alert_threshold", 0),
            aging_days=d.get("aging_days", 0), abc_a_threshold=d.get("abc_a_threshold", 0.8),
            abc_b_threshold=d.get("abc_b_threshold", 0.95), periodic_days=d.get("periodic_days", 0),
        )

    def _dict_to_action(self, d: dict) -> InvActionConfig:
        return InvActionConfig(
            action_type=d.get("action_type", "alert"),
            notify_channels=tuple(d.get("notify_channels", [])),
            notify_recipients=tuple(d.get("notify_recipients", [])),
            auto_create_order=d.get("auto_create_order", False),
            fifo_enforce=d.get("fifo_enforce", False),
            expire_action=d.get("expire_action", "warn"),
        )

    def _inv_orm_to_dict(self, orm) -> dict:
        agg = self._inv_repo.to_aggregate(orm)
        tc = agg.threshold_config
        ac = agg.action_config
        return {
            "id": str(orm.id), "tenant_id": str(orm.tenant_id),
            "strategy_key": orm.strategy_key, "strategy_name": orm.strategy_name,
            "strategy_type": orm.strategy_type, "target_ref": orm.target_ref,
            "threshold_config": {
                "safety_stock": tc.safety_stock, "min_stock": tc.min_stock, "max_stock": tc.max_stock,
                "reorder_point": tc.reorder_point, "eoq": tc.eoq, "alert_threshold": tc.alert_threshold,
                "aging_days": tc.aging_days, "abc_a_threshold": tc.abc_a_threshold,
                "abc_b_threshold": tc.abc_b_threshold, "periodic_days": tc.periodic_days,
            },
            "action_config": {
                "action_type": ac.action_type,
                "notify_channels": list(ac.notify_channels),
                "notify_recipients": list(ac.notify_recipients),
                "auto_create_order": ac.auto_create_order,
                "fifo_enforce": ac.fifo_enforce,
                "expire_action": ac.expire_action,
            },
            "scope_level": orm.scope_level, "scope_ref": orm.scope_ref,
            "priority": orm.priority, "is_active": orm.is_active == "true",
            "version": orm.version, "description": orm.description,
        }