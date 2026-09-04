"""PricingEngine 单元测试 - 优先级匹配、阶梯价、策略缺失降级、过期跳过。"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

import pytest

from app.domain.biz_ops.aggregates.pricing_strategy_aggregate import PricingStrategyAggregate
from app.domain.biz_ops.enums.enums import PricingType
from app.domain.biz_ops.services.pricing_engine import PricingEngine
from app.domain.biz_ops.value_objects.price_config import PriceConfig, TierPrice
from app.domain.shared.entity import EntityId


TENANT_ID = uuid4()


def _make_strategy(priority: int = 100, base_price: float = 100.0,
                   discount_rate: float = 0.0, is_active: bool = True,
                   effective_from=None, effective_to=None,
                   tier_prices: tuple = ()) -> PricingStrategyAggregate:
    return PricingStrategyAggregate(
        id=EntityId.generate(), tenant_id=TENANT_ID,
        strategy_key=f"ps_{priority}_{uuid4().hex[:6]}",
        strategy_name="测试策略", strategy_type=PricingType.DISCOUNT,
        target_ref="SKU001",
        price_config=PriceConfig(base_price=base_price, discount_rate=discount_rate, tier_prices=tier_prices),
        priority=priority, is_active=is_active,
        effective_from=effective_from, effective_to=effective_to,
    )


class TestPricingEngine:
    """定价求值引擎测试。"""

    def test_priority_matching(self):
        s1 = _make_strategy(priority=50, base_price=100.0)
        s2 = _make_strategy(priority=10, base_price=200.0)
        engine = PricingEngine()
        record = engine.resolve_price([s1, s2])
        assert record is not None
        assert record.base_price == 200.0

    def test_tier_price_calculation(self):
        tiers = (TierPrice(min_quantity=1, max_quantity=9, unit_price=10.0),
                 TierPrice(min_quantity=10, max_quantity=99, unit_price=8.0))
        s = _make_strategy(tier_prices=tiers)
        engine = PricingEngine()
        record = engine.resolve_price([s], quantity=50)
        assert record is not None
        assert record.final_price == 8.0

    def test_no_strategy_returns_none(self):
        engine = PricingEngine()
        record = engine.resolve_price([])
        assert record is None

    def test_inactive_strategy_skipped(self):
        s = _make_strategy(is_active=False)
        engine = PricingEngine()
        record = engine.resolve_price([s])
        assert record is None

    def test_expired_strategy_skipped(self):
        now = datetime.now(timezone.utc)
        s = _make_strategy(effective_to=now - timedelta(hours=1))
        engine = PricingEngine()
        record = engine.resolve_price([s], at=now)
        assert record is None

    def test_discount_applied(self):
        s = _make_strategy(base_price=100.0, discount_rate=0.2)
        engine = PricingEngine()
        record = engine.resolve_price([s])
        assert record is not None
        assert record.final_price == 80.0
        assert record.strategy_type == PricingType.DISCOUNT.value