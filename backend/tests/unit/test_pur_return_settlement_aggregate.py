"""PUR 退货/结算/发票/付款 聚合根单元测试。

覆盖 PurchaseReturn DRAFT→SUBMITTED→APPROVED→SHIPPED→COMPLETED、Settlement 对账一致/差异、
Invoice 匹配一致/不一致、Payment PENDING→APPROVED→EXECUTING→COMPLETED/FAILED 状态机与前置守卫。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.purchasing.aggregates.purchase_return_settlement_aggregate import (
    InvoiceAggregate,
    InvoiceStatus,
    PaymentRequestAggregate,
    PaymentStatus,
    PurchaseReturnAggregate,
    PurchaseReturnLine,
    PurchaseReturnStatus,
    PurchaseSettlementAggregate,
    SettlementStatus,
)
from app.interfaces.middleware.error_handler import PURError, PURErrorCode


def _return_line(qty: float = 2.0) -> PurchaseReturnLine:
    return PurchaseReturnLine(return_quantity=qty, reason="质量不合格")


class PurchaseReturnAggregateTest:
    """PurchaseReturnAggregate 退货状态机测试。"""

    def test_default_status_is_draft(self) -> None:
        ret = PurchaseReturnAggregate()
        assert ret.status == PurchaseReturnStatus.DRAFT
        assert ret.approved_by is None

    def test_full_lifecycle_to_completed(self) -> None:
        ret = PurchaseReturnAggregate()
        ret.lines.append(_return_line())
        ret.submit()
        assert ret.status == PurchaseReturnStatus.SUBMITTED
        approver = uuid4()
        ret.approve(approver)
        assert ret.status == PurchaseReturnStatus.APPROVED
        assert ret.approved_by == approver
        ret.ship(["tx-out-1"])
        assert ret.status == PurchaseReturnStatus.SHIPPED
        assert ret.inv_transaction_ids == ["tx-out-1"]
        assert ret.shipped_at is not None
        ret.complete()
        assert ret.status == PurchaseReturnStatus.COMPLETED

    def test_submit_without_lines_rejected(self) -> None:
        ret = PurchaseReturnAggregate()
        with pytest.raises(PURError) as exc:
            ret.submit()
        assert exc.value.code == PURErrorCode.RETURN_NOT_FOUND

    def test_approve_from_non_submitted_rejected(self) -> None:
        ret = PurchaseReturnAggregate()
        ret.lines.append(_return_line())
        with pytest.raises(PURError) as exc:
            ret.approve(uuid4())
        assert exc.value.code == PURErrorCode.RETURN_NOT_APPROVED

    def test_ship_from_non_approved_rejected(self) -> None:
        ret = PurchaseReturnAggregate()
        ret.lines.append(_return_line())
        ret.submit()
        with pytest.raises(PURError) as exc:
            ret.ship([])
        assert exc.value.code == PURErrorCode.RETURN_NOT_APPROVED

    def test_complete_from_non_shipped_rejected(self) -> None:
        ret = PurchaseReturnAggregate()
        ret.lines.append(_return_line())
        ret.submit()
        ret.approve(uuid4())
        with pytest.raises(PURError) as exc:
            ret.complete()
        assert exc.value.code == PURErrorCode.RETURN_NOT_FOUND


class PurchaseSettlementAggregateTest:
    """PurchaseSettlementAggregate 三边对账与差异解决测试。"""

    def test_default_status_is_pending(self) -> None:
        stl = PurchaseSettlementAggregate()
        assert stl.status == SettlementStatus.PENDING
        assert stl.diff_amount == 0.0

    def test_reconcile_consistent_transitions_to_reconciled(self) -> None:
        stl = PurchaseSettlementAggregate(total_amount=1000.0)
        stl.reconcile(1000.0)
        assert stl.status == SettlementStatus.RECONCILED
        assert stl.received_amount == 1000.0
        assert stl.diff_amount == 0.0
        assert stl.reconciled_at is not None

    def test_reconcile_within_tolerance_reconciled(self) -> None:
        stl = PurchaseSettlementAggregate(total_amount=1000.0)
        stl.reconcile(999.995)
        assert stl.status == SettlementStatus.RECONCILED
        assert abs(stl.diff_amount) < 0.01

    def test_reconcile_diff_found(self) -> None:
        stl = PurchaseSettlementAggregate(total_amount=1000.0)
        stl.reconcile(950.0)
        assert stl.status == SettlementStatus.DIFF_FOUND
        assert stl.diff_amount == 50.0

    def test_resolve_transitions_to_resolved(self) -> None:
        stl = PurchaseSettlementAggregate(total_amount=1000.0)
        stl.reconcile(950.0)
        stl.resolve()
        assert stl.status == SettlementStatus.RESOLVED


class InvoiceAggregateTest:
    """InvoiceAggregate 发票匹配测试。"""

    def test_default_status_is_draft(self) -> None:
        inv = InvoiceAggregate()
        assert inv.status == InvoiceStatus.DRAFT

    def test_match_exact_amount_transitions_to_matched(self) -> None:
        inv = InvoiceAggregate(invoice_amount=500.0)
        inv.match(500.0)
        assert inv.status == InvoiceStatus.MATCHED
        assert inv.matched_amount == 500.0

    def test_match_within_tolerance_matched(self) -> None:
        inv = InvoiceAggregate(invoice_amount=500.0)
        inv.match(500.005)
        assert inv.status == InvoiceStatus.MATCHED

    def test_match_diff_transitions_to_mismatched(self) -> None:
        inv = InvoiceAggregate(invoice_amount=500.0)
        inv.match(480.0)
        assert inv.status == InvoiceStatus.MISMATCHED


class PaymentRequestAggregateTest:
    """PaymentRequestAggregate 付款状态机测试。"""

    def test_default_status_is_pending(self) -> None:
        pay = PaymentRequestAggregate()
        assert pay.status == PaymentStatus.PENDING
        assert pay.paid_at is None

    def test_full_lifecycle_to_completed(self) -> None:
        pay = PaymentRequestAggregate()
        pay.approve()
        assert pay.status == PaymentStatus.APPROVED
        pay.execute(["tx-pay-1"])
        assert pay.status == PaymentStatus.EXECUTING
        assert pay.inv_transaction_ids == ["tx-pay-1"]
        pay.complete()
        assert pay.status == PaymentStatus.COMPLETED
        assert pay.paid_at is not None

    def test_approve_from_non_pending_rejected(self) -> None:
        pay = PaymentRequestAggregate()
        pay.approve()
        with pytest.raises(PURError) as exc:
            pay.approve()
        assert exc.value.code == PURErrorCode.PAYMENT_ALREADY_COMPLETED

    def test_execute_from_non_approved_rejected(self) -> None:
        pay = PaymentRequestAggregate()
        with pytest.raises(PURError) as exc:
            pay.execute([])
        assert exc.value.code == PURErrorCode.PAYMENT_NOT_FOUND

    def test_complete_from_non_executing_rejected(self) -> None:
        pay = PaymentRequestAggregate()
        pay.approve()
        with pytest.raises(PURError) as exc:
            pay.complete()
        assert exc.value.code == PURErrorCode.PAYMENT_NOT_FOUND

    def test_fail_transitions_to_failed(self) -> None:
        pay = PaymentRequestAggregate()
        pay.fail()
        assert pay.status == PaymentStatus.FAILED