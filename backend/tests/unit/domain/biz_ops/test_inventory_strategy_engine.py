"""InventoryStrategyEngine 单元测试 - 策略检查、预警、补货建议。"""

from __future__ import annotations

import os
import sys
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

import pytest

from app.domain.biz_ops.aggregates.inventory_strategy_aggregate import InventoryStrategyAggregate
from app.domain.biz_ops.enums.enums import ExecutionResult, InvStrategyType
from app.domain.biz_ops.services.inventory_strategy_engine import InventoryStrategyEngine
from app.domain.biz_ops.value_objects.inventory_strategy_config import InvActionConfig, InvThresholdConfig
from app.domain.shared.entity import EntityId


TENANT_ID = uuid4()


def _make_strategy(stype: InvStrategyType, **kw) -> InventoryStrategyAggregate:
    defaults = dict(
        id=EntityId.generate(), tenant_id=TENANT_ID,
        strategy_key=f"inv_{stype.value}_{uuid4().hex[:6]}",
        strategy_name="测试", strategy_type=stype, target_ref="SKU001",
        threshold_config=InvThresholdConfig(safety_stock=50, reorder_point=20, eoq=50, aging_days=30),
        action_config=InvActionConfig(),
    )
    defaults.update(kw)
    return InventoryStrategyAggregate(**defaults)


class TestInventoryStrategyEngine:
    """库存策略引擎测试。"""

    def test_safety_stock_alert(self):
        s = _make_strategy(InvStrategyType.SAFETY_STOCK)
        engine = InventoryStrategyEngine()
        records = engine.check_strategies([s], current_stock=30)
        assert len(records) == 1
        assert records[0].result == ExecutionResult.WARN

    def test_no_alert_when_above_safety(self):
        s = _make_strategy(InvStrategyType.SAFETY_STOCK)
        engine = InventoryStrategyEngine()
        records = engine.check_strategies([s], current_stock=60)
        assert len(records) == 0

    def test_reorder_suggestion(self):
        s = _make_strategy(InvStrategyType.REORDER)
        engine = InventoryStrategyEngine()
        records = engine.check_strategies([s], current_stock=15)
        assert len(records) == 1
        assert "建议补货" in records[0].suggestion

    def test_aging_alert(self):
        s = _make_strategy(InvStrategyType.AGING)
        engine = InventoryStrategyEngine()
        records = engine.check_strategies([s], current_stock=100, stock_age_days=45)
        assert len(records) == 1
        assert records[0].result == ExecutionResult.WARN

    def test_inactive_strategy_skipped(self):
        s = _make_strategy(InvStrategyType.SAFETY_STOCK, is_active=False)
        engine = InventoryStrategyEngine()
        records = engine.check_strategies([s], current_stock=10)
        assert len(records) == 0

    def test_multiple_strategies(self):
        s1 = _make_strategy(InvStrategyType.SAFETY_STOCK)
        s2 = _make_strategy(InvStrategyType.REORDER)
        engine = InventoryStrategyEngine()
        records = engine.check_strategies([s1, s2], current_stock=10)
        assert len(records) == 2