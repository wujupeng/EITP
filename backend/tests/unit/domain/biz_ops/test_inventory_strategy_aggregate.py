"""InventoryStrategyAggregate 单元测试 - 五类策略、阈值校验。"""

from __future__ import annotations

import os
import sys
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

import pytest

from app.domain.biz_ops.aggregates.inventory_strategy_aggregate import InventoryStrategyAggregate
from app.domain.biz_ops.enums.enums import InvStrategyType, ScopeLevel
from app.domain.biz_ops.value_objects.inventory_strategy_config import InvActionConfig, InvThresholdConfig
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import BizOpsError, BizOpsErrorCode


TENANT_ID = uuid4()


class TestInventoryStrategyAggregate:
    """库存策略聚合根测试。"""

    def _make(self, **kw) -> InventoryStrategyAggregate:
        defaults = dict(
            id=EntityId.generate(), tenant_id=TENANT_ID,
            strategy_key="inv_test", strategy_name="测试策略",
            strategy_type=InvStrategyType.SAFETY_STOCK, target_ref="SKU001",
            threshold_config=InvThresholdConfig(safety_stock=50),
            action_config=InvActionConfig(),
        )
        defaults.update(kw)
        return InventoryStrategyAggregate(**defaults)

    def test_safety_stock_strategy(self):
        agg = self._make(strategy_type=InvStrategyType.SAFETY_STOCK)
        assert agg.check_safety_stock(30) is True
        assert agg.check_safety_stock(60) is False

    def test_alert_strategy(self):
        agg = self._make(strategy_type=InvStrategyType.ALERT,
                         threshold_config=InvThresholdConfig(alert_threshold=10))
        assert agg.threshold_config.alert_threshold == 10
        assert agg.strategy_type == InvStrategyType.ALERT

    def test_reorder_strategy(self):
        agg = self._make(strategy_type=InvStrategyType.REORDER,
                         threshold_config=InvThresholdConfig(reorder_point=20, eoq=50))
        assert agg.check_reorder_needed(15) is True
        assert agg.check_reorder_needed(30) is False

    def test_aging_strategy(self):
        agg = self._make(strategy_type=InvStrategyType.AGING,
                         threshold_config=InvThresholdConfig(aging_days=30))
        assert agg.check_aging_alert(45) is True
        assert agg.check_aging_alert(20) is False

    def test_abc_strategy(self):
        agg = self._make(strategy_type=InvStrategyType.ABC,
                         threshold_config=InvThresholdConfig(abc_a_threshold=0.7, abc_b_threshold=0.9))
        assert agg.get_abc_class(0.5) == "A"
        assert agg.get_abc_class(0.8) == "B"
        assert agg.get_abc_class(0.95) == "C"

    def test_reorder_without_point_or_period_raises(self):
        with pytest.raises(BizOpsError):
            self._make(strategy_type=InvStrategyType.REORDER,
                       threshold_config=InvThresholdConfig())

    def test_aging_without_days_raises(self):
        with pytest.raises(BizOpsError):
            self._make(strategy_type=InvStrategyType.AGING,
                       threshold_config=InvThresholdConfig())

    def test_abc_invalid_thresholds_raises(self):
        with pytest.raises(BizOpsError):
            self._make(strategy_type=InvStrategyType.ABC,
                       threshold_config=InvThresholdConfig(abc_a_threshold=0.9, abc_b_threshold=0.8))

    def test_negative_threshold_raises(self):
        with pytest.raises(BizOpsError):
            self._make(threshold_config=InvThresholdConfig(safety_stock=-1))