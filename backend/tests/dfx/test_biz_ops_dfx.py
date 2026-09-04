"""BIZ-OPS DFX 测试 - 性能/可靠性/安全性指标。"""

from __future__ import annotations

import os
import sys
import time
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

import pytest

from app.domain.biz_ops.aggregates.pricing_strategy_aggregate import PricingStrategyAggregate
from app.domain.biz_ops.aggregates.tax_config_aggregate import TaxConfigAggregate, TaxRateEntry
from app.domain.biz_ops.enums.enums import PricingType, TaxType
from app.domain.biz_ops.services.pricing_engine import PricingEngine
from app.domain.biz_ops.services.tax_engine import TaxEngine
from app.domain.biz_ops.value_objects.price_config import PriceConfig
from app.domain.shared.entity import EntityId


TENANT_ID = uuid4()


class TestBizOpsPerformance:
    """性能指标测试。"""

    def test_pricing_engine_latency(self):
        strategy = PricingStrategyAggregate(
            id=EntityId.generate(), tenant_id=TENANT_ID, strategy_key="perf_test",
            strategy_name="性能测试", strategy_type=PricingType.DISCOUNT, target_ref="SKU001",
            price_config=PriceConfig(base_price=100.0, discount_rate=0.1),
        )
        engine = PricingEngine()
        start = time.perf_counter()
        for _ in range(100):
            engine.resolve_price([strategy])
        elapsed = (time.perf_counter() - start) / 100 * 1000
        assert elapsed < 50, f"定价求值 {elapsed:.2f}ms > 50ms"

    def test_tax_engine_latency(self):
        config = TaxConfigAggregate(
            id=EntityId.generate(), tenant_id=TENANT_ID, config_key="perf_tax",
            config_name="税务", tax_rates=(TaxRateEntry(tax_type=TaxType.VAT, rate=0.13, is_default=True),),
        )
        engine = TaxEngine()
        lines = [{"line_id": f"L{i}", "amount": 100.0} for i in range(10)]
        start = time.perf_counter()
        for _ in range(100):
            engine.calculate(config, lines)
        elapsed = (time.perf_counter() - start) / 100 * 1000
        assert elapsed < 100, f"税务计算 {elapsed:.2f}ms > 100ms"


class TestBizOpsReliability:
    """可靠性测试。"""

    def test_pricing_idempotent(self):
        strategy = PricingStrategyAggregate(
            id=EntityId.generate(), tenant_id=TENANT_ID, strategy_key="idem_test",
            strategy_name="幂等", strategy_type=PricingType.DISCOUNT, target_ref="SKU001",
            price_config=PriceConfig(base_price=100.0, discount_rate=0.1),
        )
        engine = PricingEngine()
        r1 = engine.resolve_price([strategy])
        r2 = engine.resolve_price([strategy])
        assert r1.final_price == r2.final_price

    def test_tax_idempotent(self):
        config = TaxConfigAggregate(
            id=EntityId.generate(), tenant_id=TENANT_ID, config_key="idem_tax",
            config_name="幂等税务", tax_rates=(TaxRateEntry(tax_type=TaxType.VAT, rate=0.13, is_default=True),),
        )
        engine = TaxEngine()
        lines = [{"line_id": "L1", "amount": 100.0}]
        r1 = engine.calculate(config, lines)
        r2 = engine.calculate(config, lines)
        assert r1.total_tax == r2.total_tax


class TestBizOpsSecurity:
    """安全性测试。"""

    def test_tenant_isolation_in_aggregate(self):
        tenant_a = uuid4()
        tenant_b = uuid4()
        s_a = PricingStrategyAggregate(
            id=EntityId.generate(), tenant_id=tenant_a, strategy_key="iso_a",
            strategy_name="A", strategy_type=PricingType.DISCOUNT, target_ref="SKU001",
            price_config=PriceConfig(base_price=100.0),
        )
        s_b = PricingStrategyAggregate(
            id=EntityId.generate(), tenant_id=tenant_b, strategy_key="iso_b",
            strategy_name="B", strategy_type=PricingType.DISCOUNT, target_ref="SKU001",
            price_config=PriceConfig(base_price=200.0),
        )
        assert s_a.tenant_id != s_b.tenant_id
        assert s_a.calculate_price() != s_b.calculate_price()

    def test_audit_record_immutable(self):
        from app.domain.biz_ops.aggregates.operation_audit_aggregate import OperationAuditAggregate
        from app.domain.biz_ops.enums.enums import OperationType
        agg = OperationAuditAggregate(
            id=EntityId.generate(), tenant_id=TENANT_ID, trace_id="sec_001",
            operation_type=OperationType.PURCHASE_ORDER_CREATE, operator_id=uuid4(),
            entity_type="purchase_order", entity_id=uuid4(),
        )
        d1 = agg.to_dict()
        d2 = agg.to_dict()
        assert d1 == d2