"""SAL SalesSettlement / SalesInvoice / PaymentReceipt + ReconcileDiffChecker / InvoiceMatchChecker 单元测试。

覆盖结算单状态机 PENDING→RECONCILED→INVOICE_MATCHED→PAYMENT_REQUESTED→PAYMENT_COMPLETED、
对账差异阈值、退货退款冲抵、发票匹配状态机与阈值、收款申请状态机、对账/发票校验服务。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.sales.aggregates.payment_receipt_aggregate import PaymentReceiptAggregate
from app.domain.sales.aggregates.sales_invoice_aggregate import SalesInvoiceAggregate
from app.domain.sales.aggregates.sales_settlement_aggregate import SalesSettlementAggregate
from app.domain.sales.entities.invoice_line import InvoiceLine
from app.domain.sales.entities.settlement_reconcile_line import SettlementReconcileLine
from app.domain.sales.services.reconcile_checkers import (
    InvoiceMatchChecker,
    ReconcileDiffChecker,
)
from app.domain.sales.value_objects.settlement_vo import (
    InvoiceStatus,
    PaymentStatus,
    SettlementStatus,
)
from app.interfaces.middleware.error_handler import SALError, SALErrorCode


def _reconcile_line(order_qty: float = 10.0, ship_qty: float = 10.0, price: float = 100.0) -> SettlementReconcileLine:
    return SettlementReconcileLine(
        order_quantity=order_qty, shipped_quantity=ship_qty, unit_price=price
    )


def _reconciled_settlement() -> SalesSettlementAggregate:
    s = SalesSettlementAggregate(settlement_code="ST-001")
    s.reconcile([_reconcile_line()], threshold=0.01, reconciled_by=uuid4())
    return s


class SalesSettlementAggregateTest:
    """SalesSettlementAggregate 结算单状态机与对账测试。"""

    def test_default_status_is_pending(self) -> None:
        s = SalesSettlementAggregate()
        assert s.status == SettlementStatus.PENDING
        assert s.is_reconciled is False

    def test_reconcile_empty_lines_rejected(self) -> None:
        s = SalesSettlementAggregate()
        with pytest.raises(SALError) as exc:
            s.reconcile([], threshold=0.01, reconciled_by=uuid4())
        assert exc.value.code == SALErrorCode.SETTLEMENT_NOT_FOUND

    def test_reconcile_diff_over_threshold_rejected(self) -> None:
        s = SalesSettlementAggregate()
        line = SettlementReconcileLine(order_quantity=10, shipped_quantity=12, unit_price=100)
        with pytest.raises(SALError) as exc:
            s.reconcile([line], threshold=0.01, reconciled_by=uuid4())
        assert exc.value.code == SALErrorCode.SETTLEMENT_RECONCILE_DIFF_EXCEEDED

    def test_reconcile_calculates_receivable_amount(self) -> None:
        s = SalesSettlementAggregate()
        s.reconcile(
            [_reconcile_line(order_qty=10, ship_qty=10, price=100),
             _reconcile_line(order_qty=5, ship_qty=5, price=200)],
            threshold=0.01, reconciled_by=uuid4(),
        )
        assert s.status == SettlementStatus.RECONCILED
        assert s.receivable_amount == 2000.0
        assert s.net_receivable_amount == 2000.0
        assert s.is_reconciled is True

    def test_apply_refund_reduces_net_receivable(self) -> None:
        s = _reconciled_settlement()
        s.apply_refund(300.0)
        assert s.refund_amount == 300.0
        assert s.net_receivable_amount == 700.0  # 1000 - 300

    def test_apply_refund_negative_rejected(self) -> None:
        s = _reconciled_settlement()
        with pytest.raises(SALError) as exc:
            s.apply_refund(-1.0)
        assert exc.value.code == SALErrorCode.SETTLEMENT_NOT_FOUND

    def test_match_invoice_within_threshold(self) -> None:
        s = _reconciled_settlement()
        inv_id = uuid4()
        s.match_invoice(inv_id, invoice_amount=1000.0, threshold=0.01)
        assert s.status == SettlementStatus.INVOICE_MATCHED
        assert s.invoice_id == inv_id

    def test_match_invoice_diff_over_threshold_rejected(self) -> None:
        s = _reconciled_settlement()
        with pytest.raises(SALError) as exc:
            s.match_invoice(uuid4(), invoice_amount=1100.0, threshold=0.01)
        assert exc.value.code == SALErrorCode.INVOICE_MATCH_DIFF_EXCEEDED

    def test_match_invoice_from_non_reconciled_rejected(self) -> None:
        s = SalesSettlementAggregate()
        # PENDING 状态 net_receivable=0，invoice_amount=100 触发金额差异校验
        with pytest.raises(SALError) as exc:
            s.match_invoice(uuid4(), 100.0, 0.01)
        assert exc.value.code == SALErrorCode.INVOICE_MATCH_DIFF_EXCEEDED

    def test_full_lifecycle_to_payment_completed(self) -> None:
        s = _reconciled_settlement()
        s.match_invoice(uuid4(), 1000.0, 0.01)
        s.request_payment(uuid4())
        assert s.status == SettlementStatus.PAYMENT_REQUESTED
        s.confirm_payment()
        assert s.status == SettlementStatus.PAYMENT_COMPLETED
        assert s.is_reconciled is True

    def test_request_payment_from_non_invoice_matched_rejected(self) -> None:
        s = _reconciled_settlement()
        with pytest.raises(SALError) as exc:
            s.request_payment(uuid4())
        assert exc.value.code == SALErrorCode.SETTLEMENT_RECONCILE_DIFF_EXCEEDED

    def test_confirm_payment_from_non_requested_rejected(self) -> None:
        s = _reconciled_settlement()
        s.match_invoice(uuid4(), 1000.0, 0.01)
        with pytest.raises(SALError) as exc:
            s.confirm_payment()
        assert exc.value.code == SALErrorCode.SETTLEMENT_RECONCILE_DIFF_EXCEEDED

    def test_mark_revenue_landed(self) -> None:
        s = _reconciled_settlement()
        s.mark_revenue_landed()
        assert s.revenue_landed is True

    def test_payment_requested_can_retry(self) -> None:
        s = _reconciled_settlement()
        s.match_invoice(uuid4(), 1000.0, 0.01)
        s.request_payment(uuid4())
        # PAYMENT_REQUESTED → PAYMENT_REQUESTED 允许重试
        s.request_payment(uuid4())
        assert s.status == SettlementStatus.PAYMENT_REQUESTED


class SettlementReconcileLineTest:
    """SettlementReconcileLine 对账明细计算测试。"""

    def test_amount_and_diff_calculation(self) -> None:
        line = SettlementReconcileLine(order_quantity=10, shipped_quantity=10, unit_price=100)
        assert line.amount == 1000.0
        assert line.diff == 0.0
        assert line.is_consistent is True

    def test_inconsistent_when_diff_present(self) -> None:
        line = SettlementReconcileLine(order_quantity=10, shipped_quantity=12, unit_price=100)
        assert line.diff == 2.0
        assert line.is_consistent is False


class SalesInvoiceAggregateTest:
    """SalesInvoiceAggregate 发票匹配状态机测试。"""

    def test_default_status_is_pending(self) -> None:
        inv = SalesInvoiceAggregate(invoice_code="INV-001")
        assert inv.status == InvoiceStatus.PENDING
        assert inv.is_matched is False

    def test_negative_invoice_amount_rejected(self) -> None:
        with pytest.raises(SALError) as exc:
            SalesInvoiceAggregate(invoice_amount=-1.0)
        assert exc.value.code == SALErrorCode.INVOICE_NOT_FOUND

    def test_negative_tax_amount_rejected(self) -> None:
        with pytest.raises(SALError) as exc:
            SalesInvoiceAggregate(tax_amount=-1.0)
        assert exc.value.code == SALErrorCode.INVOICE_NOT_FOUND

    def test_add_line_accumulates_amount(self) -> None:
        inv = SalesInvoiceAggregate()
        inv.add_line(InvoiceLine(quantity=10, unit_price=100))
        inv.add_line(InvoiceLine(quantity=5, unit_price=200))
        assert inv.invoice_amount == 2000.0

    def test_total_amount_with_tax(self) -> None:
        inv = SalesInvoiceAggregate(invoice_amount=1000.0, tax_amount=130.0)
        assert inv.total_amount_with_tax == 1130.0

    def test_match_within_threshold(self) -> None:
        inv = SalesInvoiceAggregate(invoice_amount=1000.0)
        sid = uuid4()
        inv.match(sid, expected_amount=1000.0, threshold=0.01)
        assert inv.status == InvoiceStatus.MATCHED
        assert inv.matched_settlement_id == sid
        assert inv.is_matched is True

    def test_match_diff_over_threshold_rejected(self) -> None:
        inv = SalesInvoiceAggregate(invoice_amount=1100.0)
        with pytest.raises(SALError) as exc:
            inv.match(uuid4(), expected_amount=1000.0, threshold=0.01)
        assert exc.value.code == SALErrorCode.INVOICE_MATCH_DIFF_EXCEEDED
        assert inv.status == InvoiceStatus.MISMATCHED

    def test_match_from_non_pending_rejected(self) -> None:
        inv = SalesInvoiceAggregate(invoice_amount=1000.0)
        inv.match(uuid4(), 1000.0, 0.01)
        with pytest.raises(SALError) as exc:
            inv.match(uuid4(), 1000.0, 0.01)
        assert exc.value.code == SALErrorCode.INVOICE_NOT_FOUND

    def test_invoice_line_amount_calculation(self) -> None:
        line = InvoiceLine(quantity=7, unit_price=3.5)
        assert line.amount == 24.5


class PaymentReceiptAggregateTest:
    """PaymentReceiptAggregate 收款申请状态机测试。"""

    def test_non_positive_amount_rejected(self) -> None:
        with pytest.raises(SALError) as exc:
            PaymentReceiptAggregate(payment_amount=0.0)
        assert exc.value.code == SALErrorCode.PAYMENT_NOT_FOUND

    def test_default_status_is_requested(self) -> None:
        p = PaymentReceiptAggregate(payment_amount=1000.0)
        assert p.status == PaymentStatus.REQUESTED
        assert p.is_completed is False

    def test_confirm_sets_payment_no(self) -> None:
        p = PaymentReceiptAggregate(payment_amount=1000.0)
        p.confirm("PAY-001")
        assert p.status == PaymentStatus.COMPLETED
        assert p.payment_no == "PAY-001"
        assert p.completed_at is not None
        assert p.is_completed is True

    def test_confirm_without_payment_no_rejected(self) -> None:
        p = PaymentReceiptAggregate(payment_amount=1000.0)
        with pytest.raises(SALError) as exc:
            p.confirm("")
        assert exc.value.code == SALErrorCode.PAYMENT_FAILED

    def test_fail_transitions_to_failed(self) -> None:
        p = PaymentReceiptAggregate(payment_amount=1000.0)
        p.fail()
        assert p.status == PaymentStatus.FAILED

    def test_cancel_transitions_to_cancelled(self) -> None:
        p = PaymentReceiptAggregate(payment_amount=1000.0)
        p.cancel()
        assert p.status == PaymentStatus.CANCELLED

    def test_confirm_from_completed_rejected(self) -> None:
        p = PaymentReceiptAggregate(payment_amount=1000.0)
        p.confirm("PAY-001")
        with pytest.raises(SALError) as exc:
            p.confirm("PAY-002")
        assert exc.value.code == SALErrorCode.PAYMENT_FAILED


class ReconcileDiffCheckerTest:
    """ReconcileDiffChecker 对账差异阈值校验测试。"""

    def test_check_within_threshold_returns_diff(self) -> None:
        checker = ReconcileDiffChecker(threshold=0.01)
        assert checker.check(expected=100.0, actual=100.005) == 0.0

    def test_check_over_threshold_raises(self) -> None:
        checker = ReconcileDiffChecker(threshold=0.01)
        with pytest.raises(SALError) as exc:
            checker.check(expected=100.0, actual=100.5)
        assert exc.value.code == SALErrorCode.SETTLEMENT_RECONCILE_DIFF_EXCEEDED

    def test_custom_threshold(self) -> None:
        checker = ReconcileDiffChecker(threshold=1.0)
        assert checker.check(100.0, 100.5) == 0.5


class InvoiceMatchCheckerTest:
    """InvoiceMatchChecker 发票匹配阈值校验测试。"""

    def test_check_within_threshold_returns_diff(self) -> None:
        checker = InvoiceMatchChecker(threshold=0.01)
        assert checker.check(invoice_amount=1000.0, expected_amount=1000.0) == 0.0

    def test_check_over_threshold_raises(self) -> None:
        checker = InvoiceMatchChecker(threshold=0.01)
        with pytest.raises(SALError) as exc:
            checker.check(invoice_amount=1100.0, expected_amount=1000.0)
        assert exc.value.code == SALErrorCode.INVOICE_MATCH_DIFF_EXCEEDED

    def test_custom_threshold(self) -> None:
        checker = InvoiceMatchChecker(threshold=10.0)
        # diff = invoice_amount - expected_amount
        assert checker.check(1005.0, 1000.0) == 5.0
        assert checker.check(1000.0, 1005.0) == -5.0