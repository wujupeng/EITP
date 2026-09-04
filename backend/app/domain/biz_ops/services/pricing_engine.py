"""PricingEngine - 定价求值引擎。"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.domain.biz_ops.aggregates.pricing_strategy_aggregate import PricingStrategyAggregate
from app.domain.biz_ops.services.strategy_resolver import StrategyResolver


class PricingApplyRecord:
    """定价应用记录。"""

    def __init__(self, strategy_id: UUID, strategy_type: str, base_price: float, final_price: float):
        self.strategy_id = strategy_id
        self.strategy_type = strategy_type
        self.base_price = base_price
        self.final_price = final_price


class PricingEngine:
    """定价求值引擎 - ConfigResolver 三层继承 → 优先级匹配 → 价格计算 → 记录。"""

    def resolve_price(
        self,
        strategies: list[PricingStrategyAggregate],
        quantity: float = 1.0,
        at: datetime | None = None,
    ) -> PricingApplyRecord | None:
        """求值定价 - 返回定价应用记录或 None（无匹配策略）。"""
        now = at or datetime.now(timezone.utc)
        effective_strategies = [s for s in strategies if s.is_active and s.is_effective(now)]
        if not effective_strategies:
            return None
        sorted_strategies = sorted(effective_strategies, key=lambda s: s.priority)
        strategy = sorted_strategies[0]
        final_price = strategy.calculate_price(quantity)
        return PricingApplyRecord(
            strategy_id=strategy.id.value,
            strategy_type=strategy.strategy_type.value,
            base_price=strategy.price_config.base_price,
            final_price=final_price,
        )