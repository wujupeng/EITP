"""PUR SupplierAggregate 单元测试 - 供应商治理工作流状态机 + 供货范围管理。

覆盖 DRAFT→SUBMITTED→APPROVED→ACTIVE→DISABLED→ACTIVE 主路径、REJECTED/CANCELLED 终态、
非法流转拒绝、add_scope/update_scope 前置校验、is_active/can_receive_orders 属性。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.purchasing.aggregates.supplier_aggregate import SupplierAggregate
from app.domain.purchasing.entities.supplier_scope import (
    SupplierScope,
    SupplierScopeStatus,
)
from app.domain.purchasing.value_objects.supplier_vo import (
    BankAccount,
    SupplierStatus,
    SupplierType,
)
from app.interfaces.middleware.error_handler import PURError, PURErrorCode


def _active_supplier() -> SupplierAggregate:
    """构造一个已走完 DRAFT→SUBMITTED→APPROVED→ACTIVE 的供应商。"""
    sup = SupplierAggregate(supplier_code="S-001", supplier_name="ACME")
    sup.submit()
    sup.approve(uuid4())
    sup.publish()
    return sup


class SupplierAggregateTest:
    """SupplierAggregate 状态机与供货范围管理测试。"""

    def test_default_status_is_draft(self) -> None:
        sup = SupplierAggregate()
        assert sup.status == SupplierStatus.DRAFT
        assert sup.governance_state == "draft"
        assert sup.published_version == 0
        assert sup.is_active is False
        assert sup.can_receive_orders is False

    def test_submit_transitions_to_submitted(self) -> None:
        sup = SupplierAggregate()
        sup.submit()
        assert sup.status == SupplierStatus.SUBMITTED
        assert sup.governance_state == "submitted"

    def test_full_lifecycle_draft_to_disabled_and_reactivate(self) -> None:
        sup = SupplierAggregate()
        sup.submit()
        sup.approve(uuid4(), opinion="ok")
        assert sup.status == SupplierStatus.APPROVED
        assert sup.governance_state == "approved"
        sup.publish()
        assert sup.status == SupplierStatus.ACTIVE
        assert sup.published_version == 1
        assert sup.governance_state == "published"
        assert sup.is_active is True
        assert sup.can_receive_orders is True
        sup.disable()
        assert sup.status == SupplierStatus.DISABLED
        assert sup.is_active is False
        # DISABLED 可重新发布回 ACTIVE
        sup.publish()
        assert sup.status == SupplierStatus.ACTIVE
        assert sup.published_version == 2

    def test_reject_from_submitted_sets_rejected_terminal(self) -> None:
        sup = SupplierAggregate()
        sup.submit()
        sup.reject(uuid4(), opinion="bad")
        assert sup.status == SupplierStatus.REJECTED
        assert sup.governance_state == "rejected"
        # REJECTED 为终态，任何流转均非法
        with pytest.raises(PURError) as exc:
            sup.submit()
        assert exc.value.code == PURErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_cancel_from_draft(self) -> None:
        sup = SupplierAggregate()
        sup.cancel()
        assert sup.status == SupplierStatus.CANCELLED
        # CANCELLED 终态
        with pytest.raises(PURError) as exc:
            sup.submit()
        assert exc.value.code == PURErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_submit_from_non_draft_rejected(self) -> None:
        sup = SupplierAggregate()
        sup.submit()
        with pytest.raises(PURError) as exc:
            sup.submit()
        assert exc.value.code == PURErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_approve_from_draft_rejected(self) -> None:
        sup = SupplierAggregate()
        with pytest.raises(PURError) as exc:
            sup.approve(uuid4())
        assert exc.value.code == PURErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_publish_from_submitted_rejected(self) -> None:
        sup = SupplierAggregate()
        sup.submit()
        with pytest.raises(PURError) as exc:
            sup.publish()
        assert exc.value.code == PURErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_disable_from_active_only(self) -> None:
        sup = SupplierAggregate()
        sup.submit()
        sup.approve(uuid4())
        # APPROVED 不能直接 disable
        with pytest.raises(PURError) as exc:
            sup.disable()
        assert exc.value.code == PURErrorCode.ORDER_INVALID_STATE_TRANSITION
        sup.publish()
        sup.disable()
        assert sup.status == SupplierStatus.DISABLED
        # DISABLED 不能再 disable
        with pytest.raises(PURError) as exc:
            sup.disable()
        assert exc.value.code == PURErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_invalid_transition_message_contains_states(self) -> None:
        sup = SupplierAggregate()
        with pytest.raises(PURError) as exc:
            sup.disable()
        msg = exc.value.message
        assert "draft" in msg
        assert "disabled" in msg

    def test_add_scope_requires_active_supplier(self) -> None:
        sup = SupplierAggregate()
        scope = SupplierScope(enterprise_sku_id=uuid4())
        with pytest.raises(PURError) as exc:
            sup.add_scope(scope)
        assert exc.value.code == PURErrorCode.SUPPLIER_NOT_ACTIVE

    def test_add_scope_success_on_active_supplier(self) -> None:
        sup = _active_supplier()
        sku = uuid4()
        scope = SupplierScope(enterprise_sku_id=sku, agreement_price=12.5)
        sup.add_scope(scope)
        assert len(sup.scopes) == 1
        assert sup.scopes[0].enterprise_sku_id == sku

    def test_add_scope_duplicate_sku_rejected(self) -> None:
        sup = _active_supplier()
        sku = uuid4()
        sup.add_scope(SupplierScope(enterprise_sku_id=sku))
        with pytest.raises(PURError) as exc:
            sup.add_scope(SupplierScope(enterprise_sku_id=sku))
        assert exc.value.code == PURErrorCode.SUPPLIER_SCOPE_MISMATCH

    def test_update_scope_existing_attributes(self) -> None:
        sup = _active_supplier()
        scope = SupplierScope(enterprise_sku_id=uuid4(), agreement_price=10.0)
        sup.add_scope(scope)
        sup.update_scope(scope.scope_id, agreement_price=20.0, lead_time_days=7)
        assert scope.agreement_price == 20.0
        assert scope.lead_time_days == 7

    def test_update_scope_unknown_id_rejected(self) -> None:
        sup = _active_supplier()
        with pytest.raises(PURError) as exc:
            sup.update_scope(uuid4(), agreement_price=1.0)
        assert exc.value.code == PURErrorCode.SUPPLIER_SCOPE_MISMATCH

    def test_update_scope_ignores_unknown_attributes(self) -> None:
        sup = _active_supplier()
        scope = SupplierScope(enterprise_sku_id=uuid4())
        sup.add_scope(scope)
        # 不存在的属性应被静默忽略，不报错
        sup.update_scope(scope.scope_id, non_existing_attr="x")
        assert not hasattr(scope, "non_existing_attr")

    def test_bank_account_masking_from_raw(self) -> None:
        ba = BankAccount.from_raw(bank_name="ICBC", account_number="1234567890")
        assert ba.bank_name == "ICBC"
        assert ba.account_number_masked == "******7890"
        assert ba.last_four == "7890"

    def test_bank_account_masking_short_account_kept_as_is(self) -> None:
        ba = BankAccount.from_raw(bank_name="BOC", account_number="1234")
        assert ba.account_number_masked == "1234"
        assert ba.last_four == "1234"

    def test_supplier_type_default_distributor(self) -> None:
        sup = SupplierAggregate()
        assert sup.supplier_type == SupplierType.DISTRIBUTOR

    def test_scope_activate_deactivate_toggles_is_active(self) -> None:
        scope = SupplierScope(enterprise_sku_id=uuid4())
        assert scope.is_active is True
        scope.deactivate()
        assert scope.status == SupplierScopeStatus.INACTIVE
        assert scope.is_active is False
        scope.activate()
        assert scope.is_active is True