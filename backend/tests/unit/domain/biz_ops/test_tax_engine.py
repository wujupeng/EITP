"""TaxEngine 单元测试 - 含税不含税公式、特殊规则、多行计算。"""

from __future__ import annotations

import os
import sys
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

import pytest

from app.domain.biz_ops.aggregates.tax_config_aggregate import (
    SpecialTaxRule,
    TaxConfigAggregate,
    TaxRateEntry,
)
from app.domain.biz_ops.enums.enums import TaxDirection, TaxFlag, TaxType
from app.domain.biz_ops.services.tax_engine import TaxEngine
from app.domain.shared.entity import EntityId


TENANT_ID = uuid4()


def _make_config(**kw) -> TaxConfigAggregate:
    defaults = dict(
        id=EntityId.generate(), tenant_id=TENANT_ID,
        config_key="vat_cfg", config_name="增值税",
        tax_rates=(TaxRateEntry(tax_type=TaxType.VAT, rate=0.13, is_default=True),),
    )
    defaults.update(kw)
    return TaxConfigAggregate(**defaults)


class TestTaxEngine:
    """税务计算引擎测试。"""

    def test_exclusive_tax(self):
        config = _make_config()
        engine = TaxEngine()
        result = engine.calculate(config, [{"line_id": "L1", "amount": 100.0}])
        assert result.lines[0].base_amount == 100.0
        assert result.lines[0].tax_amount == pytest.approx(13.0)
        assert result.lines[0].total_amount == pytest.approx(113.0)

    def test_inclusive_tax(self):
        config = _make_config(tax_flag=TaxFlag.TAX_INCLUSIVE)
        engine = TaxEngine()
        result = engine.calculate(config, [{"line_id": "L1", "amount": 113.0}])
        assert result.lines[0].base_amount == pytest.approx(100.0)
        assert result.lines[0].tax_amount == pytest.approx(13.0)
        assert result.lines[0].total_amount == pytest.approx(113.0)

    def test_exempt(self):
        config = _make_config(special_rules=(SpecialTaxRule(rule="exempt"),))
        engine = TaxEngine()
        result = engine.calculate(config, [{"line_id": "L1", "amount": 100.0}])
        assert result.total_tax == 0.0

    def test_zero_rate(self):
        config = _make_config(special_rules=(SpecialTaxRule(rule="zero_rate"),))
        engine = TaxEngine()
        result = engine.calculate(config, [{"line_id": "L1", "amount": 100.0}])
        assert result.total_tax == 0.0

    def test_not_taxable(self):
        config = _make_config(special_rules=(SpecialTaxRule(rule="not_taxable"),))
        engine = TaxEngine()
        result = engine.calculate(config, [{"line_id": "L1", "amount": 100.0}])
        assert result.total_tax == 0.0
        assert result.total_amount == 100.0

    def test_multi_line(self):
        config = _make_config()
        engine = TaxEngine()
        result = engine.calculate(config, [
            {"line_id": "L1", "amount": 100.0},
            {"line_id": "L2", "amount": 200.0},
        ])
        assert len(result.lines) == 2
        assert result.total_tax == pytest.approx(39.0)
        assert result.total_amount == pytest.approx(339.0)