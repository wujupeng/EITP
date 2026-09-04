"""TaxConfigAggregate 单元测试 - 多税种多税率、含税不含税、特殊规则。"""

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
from app.domain.biz_ops.enums.enums import TaxDirection, TaxFlag, TaxScopeLevel, TaxType
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import BizOpsError, BizOpsErrorCode


TENANT_ID = uuid4()


class TestTaxConfigAggregate:
    """税务配置聚合根测试。"""

    def _make(self, **kw) -> TaxConfigAggregate:
        defaults = dict(
            id=EntityId.generate(), tenant_id=TENANT_ID,
            config_key="vat_config", config_name="增值税配置",
            tax_rates=(TaxRateEntry(tax_type=TaxType.VAT, rate=0.13, is_default=True),),
        )
        defaults.update(kw)
        return TaxConfigAggregate(**defaults)

    def test_multi_tax_rates(self):
        agg = self._make(tax_rates=(
            TaxRateEntry(tax_type=TaxType.VAT, rate=0.13, is_default=True),
            TaxRateEntry(tax_type=TaxType.VAT, rate=0.09),
            TaxRateEntry(tax_type=TaxType.VAT, rate=0.06),
        ))
        assert agg.get_default_rate(TaxType.VAT) == 0.13

    def test_multi_tax_types(self):
        agg = self._make(tax_rates=(
            TaxRateEntry(tax_type=TaxType.VAT, rate=0.13, is_default=True),
            TaxRateEntry(tax_type=TaxType.SURTAX, rate=0.12, is_default=True),
        ))
        assert agg.get_default_rate(TaxType.VAT) == 0.13
        assert agg.get_default_rate(TaxType.SURTAX) == 0.12

    def test_tax_inclusive_flag(self):
        agg = self._make(tax_flag=TaxFlag.TAX_INCLUSIVE)
        assert agg.tax_flag == TaxFlag.TAX_INCLUSIVE

    def test_input_direction(self):
        agg = self._make(direction=TaxDirection.INPUT)
        assert agg.direction == TaxDirection.INPUT

    def test_exempt_rule(self):
        agg = self._make(special_rules=(SpecialTaxRule(rule="exempt"),))
        assert agg.is_exempt() is True

    def test_zero_rate_rule(self):
        agg = self._make(special_rules=(SpecialTaxRule(rule="zero_rate"),))
        assert agg.is_zero_rate() is True

    def test_not_taxable_rule(self):
        agg = self._make(special_rules=(SpecialTaxRule(rule="not_taxable"),))
        assert agg.is_not_taxable() is True

    def test_invalid_rate_raises(self):
        with pytest.raises(BizOpsError):
            self._make(tax_rates=(TaxRateEntry(tax_type=TaxType.VAT, rate=1.5),))

    def test_empty_rates_raises(self):
        with pytest.raises(BizOpsError):
            self._make(tax_rates=())

    def test_company_scope_requires_ref(self):
        with pytest.raises(BizOpsError):
            self._make(scope_level=TaxScopeLevel.COMPANY)