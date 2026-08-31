"""PUR SupplierScopeValidator 单元测试 - 供货范围校验与协议价查询。

覆盖 validate 对非 ACTIVE 供应商、无匹配 scope、inactive scope、命中 scope 的分支，
以及 get_agreement_price 命中/未命中返回。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.purchasing.aggregates.supplier_aggregate import SupplierAggregate
from app.domain.purchasing.entities.supplier_scope import SupplierScope
from app.domain.purchasing.value_objects.supplier_vo import SupplierStatus
from app.domain.purchasing.services.supplier_scope_validator import SupplierScopeValidator
from app.interfaces.middleware.error_handler import PURError, PURErrorCode


def _active_supplier_with_scope(sku_id, price: float = 15.0) -> SupplierAggregate:
    sup = SupplierAggregate()
    sup.submit()
    sup.approve(uuid4())
    sup.publish()
    sup.add_scope(SupplierScope(enterprise_sku_id=sku_id, agreement_price=price))
    return sup


class SupplierScopeValidatorTest:
    """SupplierScopeValidator 供货范围校验测试。"""

    def test_validate_returns_true_when_scope_matches(self) -> None:
        sku = uuid4()
        sup = _active_supplier_with_scope(sku)
        assert SupplierScopeValidator.validate(sup, sku) is True

    def test_validate_rejects_inactive_supplier(self) -> None:
        sup = SupplierAggregate(status=SupplierStatus.DRAFT)
        with pytest.raises(PURError) as exc:
            SupplierScopeValidator.validate(sup, uuid4())
        assert exc.value.code == PURErrorCode.SUPPLIER_NOT_ACTIVE

    def test_validate_rejects_unknown_sku(self) -> None:
        sup = _active_supplier_with_scope(uuid4())
        with pytest.raises(PURError) as exc:
            SupplierScopeValidator.validate(sup, uuid4())
        assert exc.value.code == PURErrorCode.SUPPLIER_SCOPE_MISMATCH

    def test_validate_rejects_inactive_scope(self) -> None:
        sku = uuid4()
        sup = _active_supplier_with_scope(sku)
        # 将 scope 置为 inactive
        sup.scopes[0].deactivate()
        with pytest.raises(PURError) as exc:
            SupplierScopeValidator.validate(sup, sku)
        assert exc.value.code == PURErrorCode.SUPPLIER_SCOPE_MISMATCH

    def test_get_agreement_price_returns_price_when_matched(self) -> None:
        sku = uuid4()
        sup = _active_supplier_with_scope(sku, price=42.0)
        assert SupplierScopeValidator.get_agreement_price(sup, sku) == 42.0

    def test_get_agreement_price_returns_none_when_not_matched(self) -> None:
        sup = _active_supplier_with_scope(uuid4())
        assert SupplierScopeValidator.get_agreement_price(sup, uuid4()) is None

    def test_get_agreement_price_ignores_inactive_scope(self) -> None:
        sku = uuid4()
        sup = _active_supplier_with_scope(sku, price=42.0)
        sup.scopes[0].deactivate()
        assert SupplierScopeValidator.get_agreement_price(sup, sku) is None