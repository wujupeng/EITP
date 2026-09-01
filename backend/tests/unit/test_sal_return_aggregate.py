"""SAL SalesReturnAggregate + RefundCalculator 单元测试 - 退货状态机 + 退货数量校验 + QC 处置 + 退款计算。

覆盖 DRAFT→SUBMITTED→APPROVED→RECEIVING→QC_PENDING→COMPLETED 主路径、REJECTED/FAILED/CANCELLED 终态、
退货数量不超原发货可用量、QC 结论驱动处置决策、complete 守卫、RefundCalculator 退款计算。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.sales.aggregates.sales_return_aggregate import SalesReturnAggregate
from app.domain.sales.entities.return_line import ReturnLine
from app.domain.sales.services.refund_calculator import RefundCalculator
from app.domain.sales.value_objects.sales_return_vo import (
    Disposition,
    QcResult,
    SalesReturnStatus,
)
from app.interfaces.middleware.error_handler import SALError, SALErrorCode


def _return_line(qty: float = 5.0, price: float = 100.0) -> ReturnLine:
    return ReturnLine(return_quantity=qty, unit_price=price)


def _submitted_return() -> SalesReturnAggregate:
    r = SalesReturnAggregate(return_code="SR-001", idempotency_key="idem-sr-001")
    r.add_line(_return_line(), available_qty=10.0)
    r.submit(uuid4())
    return r


def _qc_pending_return() -> SalesReturnAggregate:
    r = _submitted_return()
    r.approve(uuid4())
    r.receive(uuid4(), ["inv-tx-1"])
    r.enter_qc_pending()
    return r


class SalesReturnAggregateTest:
    """SalesReturnAggregate 退货状态机与数量校验测试。"""

    def test_default_status_is_draft(self) -> None:
        r = SalesReturnAggregate()
        assert r.status == SalesReturnStatus.DRAFT
        assert r.total_return_quantity == 0.0

    def test_return_line_non_positive_quantity_rejected(self) -> None:
        with pytest.raises(SALError) as exc:
            ReturnLine(return_quantity=0, unit_price=10)
        assert exc.value.code == SALErrorCode.RETURN_OVER_RETURNED

    def test_return_line_negative_price_rejected(self) -> None:
        with pytest.raises(SALError) as exc:
            ReturnLine(return_quantity=5, unit_price=-1)
        assert exc.value.code == SALErrorCode.RETURN_OVER_RETURNED

    def test_return_line_refund_amount(self) -> None:
        line = ReturnLine(return_quantity=5, unit_price=100)
        assert line.refund_amount == 500.0

    def test_add_line_over_available_rejected(self) -> None:
        r = SalesReturnAggregate()
        with pytest.raises(SALError) as exc:
            r.add_line(_return_line(qty=15.0), available_qty=10.0)
        assert exc.value.code == SALErrorCode.RETURN_OVER_RETURNED

    def test_add_line_accumulates_refund_amount(self) -> None:
        r = SalesReturnAggregate()
        r.add_line(ReturnLine(return_quantity=5, unit_price=100), available_qty=10.0)
        r.add_line(ReturnLine(return_quantity=2, unit_price=50), available_qty=10.0)
        assert r.refund_amount == 600.0
        assert r.total_return_quantity == 7.0

    def test_submit_without_lines_rejected(self) -> None:
        r = SalesReturnAggregate(idempotency_key="idem")
        with pytest.raises(SALError) as exc:
            r.submit(uuid4())
        assert exc.value.code == SALErrorCode.RETURN_NOT_FOUND

    def test_submit_without_idempotency_key_rejected(self) -> None:
        r = SalesReturnAggregate()
        r.add_line(_return_line(), available_qty=10.0)
        with pytest.raises(SALError) as exc:
            r.submit(uuid4())
        assert exc.value.code == SALErrorCode.IDEMPOTENCY_KEY_REQUIRED

    def test_submit_transitions_to_submitted(self) -> None:
        r = _submitted_return()
        assert r.status == SalesReturnStatus.SUBMITTED

    def test_full_lifecycle_to_completed(self) -> None:
        r = _qc_pending_return()
        line = r.lines[0]
        r.record_qc(line.line_id, QcResult.PASSED)
        r.dispose(line.line_id, Disposition.RESTOCK)
        r.complete()
        assert r.status == SalesReturnStatus.COMPLETED

    def test_approve_sets_approved_by(self) -> None:
        r = _submitted_return()
        approver = uuid4()
        r.approve(approver)
        assert r.status == SalesReturnStatus.APPROVED
        assert r.approved_by == approver

    def test_reject_from_submitted_terminal(self) -> None:
        r = _submitted_return()
        r.reject(uuid4())
        assert r.status == SalesReturnStatus.REJECTED
        with pytest.raises(SALError) as exc:
            r.approve(uuid4())
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_receive_from_non_approved_rejected(self) -> None:
        r = _submitted_return()
        with pytest.raises(SALError) as exc:
            r.receive(uuid4(), [])
        assert exc.value.code == SALErrorCode.RETURN_NOT_APPROVED

    def test_receive_sets_wms_receiving_id(self) -> None:
        r = _submitted_return()
        r.approve(uuid4())
        rid = uuid4()
        r.receive(rid, ["tx-1"])
        assert r.status == SalesReturnStatus.RECEIVING
        assert r.wms_receiving_id == rid

    def test_record_qc_unknown_line_rejected(self) -> None:
        r = _qc_pending_return()
        with pytest.raises(SALError) as exc:
            r.record_qc(uuid4(), QcResult.PASSED)
        assert exc.value.code == SALErrorCode.RETURN_NOT_FOUND

    def test_dispose_without_qc_rejected(self) -> None:
        r = _qc_pending_return()
        line = r.lines[0]
        with pytest.raises(SALError) as exc:
            r.dispose(line.line_id, Disposition.RESTOCK)
        assert exc.value.code == SALErrorCode.RETURN_NOT_APPROVED

    def test_complete_without_qc_rejected(self) -> None:
        r = _qc_pending_return()
        with pytest.raises(SALError) as exc:
            r.complete()
        assert exc.value.code == SALErrorCode.RETURN_NOT_APPROVED

    def test_complete_without_disposition_rejected(self) -> None:
        r = _qc_pending_return()
        line = r.lines[0]
        r.record_qc(line.line_id, QcResult.PASSED)
        with pytest.raises(SALError) as exc:
            r.complete()
        assert exc.value.code == SALErrorCode.RETURN_NOT_APPROVED

    def test_cancel_from_draft(self) -> None:
        r = SalesReturnAggregate()
        r.add_line(_return_line(), available_qty=10.0)
        r.cancel()
        assert r.status == SalesReturnStatus.CANCELLED

    def test_cancelled_is_terminal(self) -> None:
        r = _submitted_return()
        r.cancel()
        with pytest.raises(SALError) as exc:
            r.approve(uuid4())
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_mark_failed_from_receiving(self) -> None:
        r = _submitted_return()
        r.approve(uuid4())
        r.receive(uuid4(), [])
        r.mark_failed()
        assert r.status == SalesReturnStatus.FAILED

    def test_mark_failed_from_completed_rejected(self) -> None:
        r = _qc_pending_return()
        line = r.lines[0]
        r.record_qc(line.line_id, QcResult.PASSED)
        r.dispose(line.line_id, Disposition.RESTOCK)
        r.complete()
        with pytest.raises(SALError) as exc:
            r.mark_failed()
        assert exc.value.code == SALErrorCode.RETURN_RECEIVING_FAILED

    def test_qc_failed_drives_quarantine_disposition(self) -> None:
        r = _qc_pending_return()
        line = r.lines[0]
        r.record_qc(line.line_id, QcResult.FAILED)
        r.dispose(line.line_id, Disposition.QUARANTINE)
        assert line.qc_result == QcResult.FAILED
        assert line.disposition == Disposition.QUARANTINE
        r.complete()
        assert r.status == SalesReturnStatus.COMPLETED

    def test_dispose_unknown_line_rejected(self) -> None:
        r = _qc_pending_return()
        line = r.lines[0]
        r.record_qc(line.line_id, QcResult.PASSED)
        with pytest.raises(SALError) as exc:
            r.dispose(uuid4(), Disposition.RESTOCK)
        assert exc.value.code == SALErrorCode.RETURN_NOT_FOUND

    def test_qc_partial_passed_drives_scrap_disposition(self) -> None:
        r = _qc_pending_return()
        line = r.lines[0]
        r.record_qc(line.line_id, QcResult.PARTIAL_PASSED)
        r.dispose(line.line_id, Disposition.SCRAP)
        r.complete()
        assert r.status == SalesReturnStatus.COMPLETED


class RefundCalculatorTest:
    """RefundCalculator 退款金额计算测试。"""

    def test_calculate_basic_refund(self) -> None:
        assert RefundCalculator.calculate(5.0, 100.0) == 500.0

    def test_calculate_with_depreciation(self) -> None:
        assert RefundCalculator.calculate(5.0, 100.0, depreciation=50.0) == 450.0

    def test_calculate_negative_quantity_returns_zero(self) -> None:
        assert RefundCalculator.calculate(-1.0, 100.0) == 0.0

    def test_calculate_negative_price_returns_zero(self) -> None:
        assert RefundCalculator.calculate(5.0, -1.0) == 0.0

    def test_calculate_negative_depreciation_returns_zero(self) -> None:
        assert RefundCalculator.calculate(5.0, 100.0, depreciation=-1.0) == 0.0

    def test_calculate_floor_at_zero(self) -> None:
        # 折损超过货值 → 退款不低于 0
        assert RefundCalculator.calculate(5.0, 100.0, depreciation=600.0) == 0.0

    def test_calculate_for_lines_sums_refund_amounts(self) -> None:
        lines = [
            ReturnLine(return_quantity=5, unit_price=100),
            ReturnLine(return_quantity=2, unit_price=50),
        ]
        assert RefundCalculator.calculate_for_lines(lines) == 600.0

    def test_calculate_for_lines_empty(self) -> None:
        assert RefundCalculator.calculate_for_lines([]) == 0.0