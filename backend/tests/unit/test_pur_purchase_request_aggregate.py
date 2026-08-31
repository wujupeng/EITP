"""PUR PurchaseRequestAggregate 单元测试 - 采购申请状态机 + 预算行累计。

覆盖 DRAFT→SUBMITTED→APPROVED→CONVERTED/CANCELLED 主路径、REJECTED 终态、
submit 空明细拒绝、add_line 正数与金额累计、is_approved 属性。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.purchasing.aggregates.purchase_request_aggregate import (
    PurchaseRequestAggregate,
    PurchaseRequestLine,
    PurchaseRequestStatus,
)
from app.interfaces.middleware.error_handler import PURError, PURErrorCode


def _line(qty: float = 5.0, price: float | None = 50.0) -> PurchaseRequestLine:
    return PurchaseRequestLine(quantity=qty, unit_price=price)


class PurchaseRequestAggregateTest:
    """PurchaseRequestAggregate 状态机与申请行累计测试。"""

    def test_default_status_is_draft(self) -> None:
        req = PurchaseRequestAggregate()
        assert req.status == PurchaseRequestStatus.DRAFT
        assert req.is_approved is False
        assert req.total_amount == 0.0

    def test_add_line_accumulates_total_amount(self) -> None:
        req = PurchaseRequestAggregate()
        req.add_line(PurchaseRequestLine(quantity=10, unit_price=100))
        req.add_line(PurchaseRequestLine(quantity=2, unit_price=25))
        assert req.total_amount == 1050.0

    def test_add_line_without_unit_price_skips_amount(self) -> None:
        req = PurchaseRequestAggregate()
        req.add_line(PurchaseRequestLine(quantity=10, unit_price=None))
        assert req.total_amount == 0.0
        assert len(req.lines) == 1

    def test_add_line_non_positive_quantity_rejected(self) -> None:
        req = PurchaseRequestAggregate()
        with pytest.raises(PURError) as exc:
            req.add_line(PurchaseRequestLine(quantity=0, unit_price=10))
        assert exc.value.code == PURErrorCode.REQUEST_BUDGET_EXCEEDED

    def test_submit_without_lines_rejected(self) -> None:
        req = PurchaseRequestAggregate()
        with pytest.raises(PURError) as exc:
            req.submit()
        assert exc.value.code == PURErrorCode.REQUEST_NOT_FOUND

    def test_full_lifecycle_to_converted(self) -> None:
        req = PurchaseRequestAggregate(request_code="PR-001")
        req.add_line(_line())
        req.submit()
        assert req.status == PurchaseRequestStatus.SUBMITTED
        approver = uuid4()
        req.approve(approver)
        assert req.status == PurchaseRequestStatus.APPROVED
        assert req.approved_by == approver
        assert req.approved_at is not None
        assert req.is_approved is True
        order_id = uuid4()
        req.convert(order_id)
        assert req.status == PurchaseRequestStatus.CONVERTED
        assert req.converted_order_id == order_id

    def test_reject_from_submitted_terminal(self) -> None:
        req = PurchaseRequestAggregate()
        req.add_line(_line())
        req.submit()
        req.reject()
        assert req.status == PurchaseRequestStatus.REJECTED
        with pytest.raises(PURError) as exc:
            req.approve(uuid4())
        assert exc.value.code == PURErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_cancel_from_approved(self) -> None:
        req = PurchaseRequestAggregate()
        req.add_line(_line())
        req.submit()
        req.approve(uuid4())
        req.cancel()
        assert req.status == PurchaseRequestStatus.CANCELLED

    def test_convert_from_draft_rejected(self) -> None:
        req = PurchaseRequestAggregate()
        req.add_line(_line())
        with pytest.raises(PURError) as exc:
            req.convert(uuid4())
        assert exc.value.code == PURErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_approve_from_draft_rejected(self) -> None:
        req = PurchaseRequestAggregate()
        req.add_line(_line())
        with pytest.raises(PURError) as exc:
            req.approve(uuid4())
        assert exc.value.code == PURErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_cancel_from_converted_terminal_rejected(self) -> None:
        req = PurchaseRequestAggregate()
        req.add_line(_line())
        req.submit()
        req.approve(uuid4())
        req.convert(uuid4())
        with pytest.raises(PURError) as exc:
            req.cancel()
        assert exc.value.code == PURErrorCode.ORDER_INVALID_STATE_TRANSITION