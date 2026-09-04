"""PricingStrategyAggregate 单元测试 - 11种定价方法、有效期、价格配置合法性。"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

import pytest

from app.domain.biz_ops.aggregates.pricing_strategy_aggregate import PricingStrategyAggregate
from app.domain.biz_ops.enums.enums import PricingType, ScopeLevel
from app.domain.biz_ops.value_objects.price_config import PriceConfig, TierPrice
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import BizOpsError, BizOpsErrorCode


TENANT_ID = uuid4()


class TestPricingStrategyAggregate:
    """定价策略聚合根测试。"""

    def _make(self, **kw) -> PricingStrategyAggregate:
        defaults = dict(
            id=EntityId.generate(), tenant_id=TENANT_ID,
            strategy_key="ps_test", strategy_name="测试策略",
            strategy_type=PricingType.DISCOUNT, target_ref="SKU001",
            price_config=PriceConfig(base_price=100.0, discount_rate=0.1),
        )
        defaults.update(kw)
        return PricingStrategyAggregate(**defaults)

    def test_purchase_pricing_types(self):
        for pt in [PricingType.SUPPLIER_AGREEMENT, PricingType.FRAMEWORK, PricingType.RFQ,
                   PricingType.COST_PLUS, PricingType.HISTORY_COMPARE]:
            agg = self._make(strategy_type=pt, strategy_key=f"pur_{pt.value}")
            assert agg.strategy_type == pt

    def test_sales_pricing_types(self):
        for pt in [PricingType.CUSTOMER_AGREEMENT, PricingType.DISCOUNT, PricingType.PROMOTION,
                   PricingType.MEMBER, PricingType.TIER, PricingType.VOLUME_PRICE]:
            agg = self._make(strategy_type=pt, strategy_key=f"sal_{pt.value}")
            assert agg.strategy_type == pt

    def test_effective_period(self):
        now = datetime.now(timezone.utc)
        agg = self._make(effective_from=now - timedelta(hours=1), effective_to=now + timedelta(hours=1))
        assert agg.is_effective(now) is True

    def test_not_yet_effective(self):
        now = datetime.now(timezone.utc)
        agg = self._make(effective_from=now + timedelta(hours=1))
        assert agg.is_effective(now) is False

    def test_expired(self):
        now = datetime.now(timezone.utc)
        agg = self._make(effective_to=now - timedelta(hours=1))
        assert agg.is_effective(now) is False

    def test_negative_base_price_raises(self):
        with pytest.raises(BizOpsError) as exc:
            self._make(price_config=PriceConfig(base_price=-1.0))
        assert exc.value.code == BizOpsErrorCode.PRICING_CALCULATION_FAILED

    def test_discount_rate_out_of_range_raises(self):
        with pytest.raises(BizOpsError):
            self._make(price_config=PriceConfig(base_price=100.0, discount_rate=1.5))

    def test_empty_strategy_key_raises(self):
        with pytest.raises(BizOpsError):
            self._make(strategy_key="")

    def test_tier_price_calculation(self):
        tiers = (TierPrice(min_quantity=1, max_quantity=9, unit_price=10.0),
                 TierPrice(min_quantity=10, max_quantity=99, unit_price=8.0))
        agg = self._make(price_config=PriceConfig(base_price=100.0, tier_prices=tiers))
        assert agg.calculate_price(5) == 10.0
        assert agg.calculate_price(50) == 8.0

    def test_base_price_with_discount(self):
        agg = self._make(price_config=PriceConfig(base_price=100.0, discount_rate=0.2))
        assert agg.calculate_price(1) == 80.0

    def test_base_price_with_markup(self):
        agg = self._make(price_config=PriceConfig(base_price=100.0, markup_rate=0.1))
        assert agg.calculate_price(1) == pytest.approx(110.0)