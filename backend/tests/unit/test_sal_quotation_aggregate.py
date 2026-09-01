"""SAL SalesQuotationAggregate 单元测试 - 报价单状态机 + 有效期 + 转单。

覆盖 DRAFT→SUBMITTED→APPROVED→CONVERTED/EXPIRED 主路径、REJECTED/CANCELLED 终态、
submit 空明细拒绝、有效期校验、过期报价不可转单、转单继承行明细。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.domain.sales.aggregates.sales_quotation_aggregate import SalesQuotationAggregate
from app.domain.sales.entities.quotation_line import QuotationLine
from app.domain.sales.value_objects.sales_quotation_status import SalesQuotationStatus
from app.interfaces.middleware.error_handler import SALError, SALErrorCode


def _line(qty: float = 10.0, price: float = 100.0) -> QuotationLine:
    return QuotationLine(quantity=qty, unit_price=price)


def _submitted_quotation() -> SalesQuotationAggregate:
    q = SalesQuotationAggregate(quotation_code="Q-001")
    q.add_line(_line())
    q.submit(uuid4())
    return q


def _approved_quotation() -> SalesQuotationAggregate:
    q = _submitted_quotation()
    q.approve(uuid4())
    return q


class SalesQuotationAggregateTest:
    """SalesQuotationAggregate 报价单状态机与转单测试。"""

    def test_default_status_is_draft(self) -> None:
        q = SalesQuotationAggregate()
        assert q.status == SalesQuotationStatus.DRAFT
        assert q.total_amount == 0.0

    def test_add_line_accumulates_total(self) -> None:
        q = SalesQuotationAggregate()
        q.add_line(QuotationLine(quantity=10, unit_price=100))
        q.add_line(QuotationLine(quantity=5, unit_price=20))
        assert q.total_amount == 1100.0
        assert len(q.lines) == 2

    def test_line_amount_calculation(self) -> None:
        line = QuotationLine(quantity=3, unit_price=7.5)
        assert line.line_amount == 22.5

    def test_line_non_positive_quantity_rejected(self) -> None:
        with pytest.raises(SALError) as exc:
            QuotationLine(quantity=0, unit_price=10)
        assert exc.value.code == SALErrorCode.QUOTATION_INVALID_STATE_TRANSITION

    def test_line_non_positive_price_rejected(self) -> None:
        with pytest.raises(SALError) as exc:
            QuotationLine(quantity=10, unit_price=0)
        assert exc.value.code == SALErrorCode.QUOTATION_INVALID_STATE_TRANSITION

    def test_valid_until_before_from_rejected(self) -> None:
        now = datetime.now(timezone.utc)
        with pytest.raises(SALError) as exc:
            SalesQuotationAggregate(valid_from=now, valid_until=now - timedelta(days=1))
        assert exc.value.code == SALErrorCode.QUOTATION_EXPIRED

    def test_submit_without_lines_rejected(self) -> None:
        q = SalesQuotationAggregate(quotation_code="Q-001")
        with pytest.raises(SALError) as exc:
            q.submit(uuid4())
        assert exc.value.code == SALErrorCode.QUOTATION_NOT_FOUND

    def test_submit_transitions_to_submitted(self) -> None:
        q = _submitted_quotation()
        assert q.status == SalesQuotationStatus.SUBMITTED
        assert q.submitted_at is not None

    def test_approve_sets_approved_by(self) -> None:
        q = _submitted_quotation()
        approver = uuid4()
        q.approve(approver)
        assert q.status == SalesQuotationStatus.APPROVED
        assert q.approved_by == approver
        assert q.approved_at is not None

    def test_reject_from_submitted_terminal(self) -> None:
        q = _submitted_quotation()
        q.reject(uuid4())
        assert q.status == SalesQuotationStatus.REJECTED
        with pytest.raises(SALError) as exc:
            q.approve(uuid4())
        assert exc.value.code == SALErrorCode.QUOTATION_INVALID_STATE_TRANSITION

    def test_cancel_from_draft(self) -> None:
        q = SalesQuotationAggregate(quotation_code="Q-001")
        q.add_line(_line())
        q.cancel()
        assert q.status == SalesQuotationStatus.CANCELLED

    def test_cancel_from_submitted(self) -> None:
        q = _submitted_quotation()
        q.cancel()
        assert q.status == SalesQuotationStatus.CANCELLED

    def test_cancelled_is_terminal(self) -> None:
        q = _submitted_quotation()
        q.cancel()
        with pytest.raises(SALError) as exc:
            q.approve(uuid4())
        assert exc.value.code == SALErrorCode.QUOTATION_INVALID_STATE_TRANSITION

    def test_approve_from_draft_rejected(self) -> None:
        q = SalesQuotationAggregate(quotation_code="Q-001")
        q.add_line(_line())
        with pytest.raises(SALError) as exc:
            q.approve(uuid4())
        assert exc.value.code == SALErrorCode.QUOTATION_INVALID_STATE_TRANSITION

    def test_convert_to_order_from_approved(self) -> None:
        q = _approved_quotation()
        order_id = q.convert_to_order()
        assert q.status == SalesQuotationStatus.CONVERTED
        assert q.converted_order_id == order_id

    def test_convert_to_order_from_non_approved_rejected(self) -> None:
        q = _submitted_quotation()
        with pytest.raises(SALError) as exc:
            q.convert_to_order()
        assert exc.value.code == SALErrorCode.QUOTATION_NOT_APPROVED

    def test_convert_to_order_from_converted_rejected(self) -> None:
        q = _approved_quotation()
        q.convert_to_order()
        with pytest.raises(SALError) as exc:
            q.convert_to_order()
        assert exc.value.code == SALErrorCode.QUOTATION_NOT_APPROVED

    def test_expired_quotation_cannot_convert(self) -> None:
        now = datetime.now(timezone.utc)
        q = SalesQuotationAggregate(
            valid_from=now - timedelta(days=2),
            valid_until=now - timedelta(days=1),
        )
        q.add_line(_line())
        q.submit(uuid4())
        q.approve(uuid4())
        with pytest.raises(SALError) as exc:
            q.convert_to_order()
        assert exc.value.code == SALErrorCode.QUOTATION_EXPIRED

    def test_check_expiry_marks_expired(self) -> None:
        now = datetime.now(timezone.utc)
        q = SalesQuotationAggregate(
            valid_from=now - timedelta(days=2),
            valid_until=now - timedelta(days=1),
        )
        q.add_line(_line())
        q.submit(uuid4())
        q.approve(uuid4())
        assert q.check_expiry(now) is True
        assert q.status == SalesQuotationStatus.EXPIRED

    def test_check_expiry_not_approved_returns_false(self) -> None:
        q = _submitted_quotation()
        assert q.check_expiry() is False
        assert q.status == SalesQuotationStatus.SUBMITTED

    def test_check_expiry_still_valid_returns_false(self) -> None:
        now = datetime.now(timezone.utc)
        q = SalesQuotationAggregate(
            valid_from=now - timedelta(days=1),
            valid_until=now + timedelta(days=1),
        )
        q.add_line(_line())
        q.submit(uuid4())
        q.approve(uuid4())
        assert q.check_expiry(now) is False
        assert q.status == SalesQuotationStatus.APPROVED

    def test_is_convertible_property(self) -> None:
        now = datetime.now(timezone.utc)
        q = SalesQuotationAggregate(
            valid_from=now - timedelta(days=1),
            valid_until=now + timedelta(days=1),
        )
        q.add_line(_line())
        assert q.is_convertible is False
        q.submit(uuid4())
        q.approve(uuid4())
        assert q.is_convertible is True

    def test_convert_inherits_lines_via_total_amount(self) -> None:
        q = SalesQuotationAggregate(quotation_code="Q-002")
        q.add_line(QuotationLine(quantity=10, unit_price=100))
        q.add_line(QuotationLine(quantity=5, unit_price=200))
        q.submit(uuid4())
        q.approve(uuid4())
        expected_total = q.total_amount
        order_id = q.convert_to_order()
        assert order_id is not None
        assert q.total_amount == expected_total
        assert len(q.lines) == 2

    def test_expired_is_terminal(self) -> None:
        now = datetime.now(timezone.utc)
        q = SalesQuotationAggregate(
            valid_from=now - timedelta(days=2),
            valid_until=now - timedelta(days=1),
        )
        q.add_line(_line())
        q.submit(uuid4())
        q.approve(uuid4())
        q.check_expiry(now)
        with pytest.raises(SALError) as exc:
            q.convert_to_order()
        assert exc.value.code == SALErrorCode.QUOTATION_NOT_APPROVED