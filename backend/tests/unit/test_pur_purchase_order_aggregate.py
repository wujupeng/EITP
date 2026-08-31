"""PUR PurchaseOrderAggregate 单元测试 - 10 态状态机 + 收货累计 + 取消守卫。

覆盖 DRAFT→SUBMITTED→APPROVED→SENT→{CHANGED,PARTIAL_RECEIVED,RECEIVED}→CLOSED 主路径、
REJECTED/CANCELLED 终态、submit 空明细拒绝、receive 累计与全收/部分收流转、cancel 已收货守卫、
add_line 正数校验、is_sent_or_later 属性。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.purchasing.aggregates.purchase_order_aggregate import (
    PurchaseOrderAggregate,
    PurchaseOrderLine,
    PurchaseOrderStatus,
)
from app.interfaces.middleware.error_handler import PURError, PURErrorCode


def _line(qty: float = 10.0, price: float = 100.0) -> PurchaseOrderLine:
    return PurchaseOrderLine(ordered_quantity=qty, unit_price=price)


def _submitted_order() -> PurchaseOrderAggregate:
    order = PurchaseOrderAggregate(order_code="PO-001")
    order.add_line(_line())
    order.submit()
    return order


def _sent_order() -> PurchaseOrderAggregate:
    order = _submitted_order()
    order.approve(uuid4())
    order.send()
    return order


class PurchaseOrderAggregateTest:
    """PurchaseOrderAggregate 10 态状态机与收货/取消守卫测试。"""

    def test_default_status_is_draft(self) -> None:
        order = PurchaseOrderAggregate()
        assert order.status == PurchaseOrderStatus.DRAFT
        assert order.total_amount == 0.0
        assert order.is_sent_or_later is False

    def test_add_line_accumulates_total_amount(self) -> None:
        order = PurchaseOrderAggregate()
        order.add_line(PurchaseOrderLine(ordered_quantity=10, unit_price=100))
        order.add_line(PurchaseOrderLine(ordered_quantity=5, unit_price=20))
        assert order.total_amount == 1100.0
        assert len(order.lines) == 2

    def test_add_line_non_positive_quantity_rejected(self) -> None:
        order = PurchaseOrderAggregate()
        with pytest.raises(PURError) as exc:
            order.add_line(PurchaseOrderLine(ordered_quantity=0, unit_price=10))
        assert exc.value.code == PURErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_submit_without_lines_rejected(self) -> None:
        order = PurchaseOrderAggregate()
        with pytest.raises(PURError) as exc:
            order.submit()
        assert exc.value.code == PURErrorCode.ORDER_NOT_FOUND

    def test_submit_with_lines_transitions_to_submitted(self) -> None:
        order = _submitted_order()
        assert order.status == PurchaseOrderStatus.SUBMITTED

    def test_full_lifecycle_to_closed(self) -> None:
        order = _sent_order()
        line = order.lines[0]
        # 部分收货
        order.receive(line.line_id, 4.0)
        assert order.status == PurchaseOrderStatus.PARTIAL_RECEIVED
        # 全收
        order.receive(line.line_id, 6.0)
        assert order.status == PurchaseOrderStatus.RECEIVED
        assert line.received_quantity == 10.0
        order.close()
        assert order.status == PurchaseOrderStatus.CLOSED
        assert order.is_sent_or_later is True

    def test_approve_sets_approved_by(self) -> None:
        order = _submitted_order()
        approver = uuid4()
        order.approve(approver)
        assert order.status == PurchaseOrderStatus.APPROVED
        assert order.approved_by == approver

    def test_reject_from_submitted(self) -> None:
        order = _submitted_order()
        order.reject()
        assert order.status == PurchaseOrderStatus.REJECTED
        # 终态
        with pytest.raises(PURError) as exc:
            order.approve(uuid4())
        assert exc.value.code == PURErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_send_sets_sent_at(self) -> None:
        order = _submitted_order()
        order.approve(uuid4())
        assert order.sent_at is None
        order.send()
        assert order.status == PurchaseOrderStatus.SENT
        assert order.sent_at is not None

    def test_send_from_non_approved_rejected(self) -> None:
        order = _submitted_order()
        with pytest.raises(PURError) as exc:
            order.send()
        assert exc.value.code == PURErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_change_from_sent(self) -> None:
        order = _sent_order()
        order.change()
        assert order.status == PurchaseOrderStatus.CHANGED
        # CHANGED 可再回到 SENT
        order.send()
        assert order.status == PurchaseOrderStatus.SENT

    def test_receive_unknown_line_rejected(self) -> None:
        order = _sent_order()
        with pytest.raises(PURError) as exc:
            order.receive(uuid4(), 1.0)
        assert exc.value.code == PURErrorCode.ORDER_LINE_NOT_FOUND

    def test_receive_full_in_one_go_transitions_to_received(self) -> None:
        order = _sent_order()
        line = order.lines[0]
        order.receive(line.line_id, 10.0)
        assert order.status == PurchaseOrderStatus.RECEIVED

    def test_receive_partial_then_full_from_changed(self) -> None:
        order = _sent_order()
        order.change()
        line = order.lines[0]
        order.receive(line.line_id, 3.0)
        assert order.status == PurchaseOrderStatus.PARTIAL_RECEIVED
        order.receive(line.line_id, 7.0)
        assert order.status == PurchaseOrderStatus.RECEIVED

    def test_cancel_from_draft_without_received(self) -> None:
        order = PurchaseOrderAggregate()
        order.add_line(_line())
        order.cancel()
        assert order.status == PurchaseOrderStatus.CANCELLED

    def test_cancel_from_sent_without_received(self) -> None:
        order = _sent_order()
        order.cancel()
        assert order.status == PurchaseOrderStatus.CANCELLED

    def test_cancel_with_received_quantity_rejected(self) -> None:
        order = _sent_order()
        line = order.lines[0]
        order.receive(line.line_id, 1.0)
        # 已收货，不可取消
        with pytest.raises(PURError) as exc:
            order.cancel()
        assert exc.value.code == PURErrorCode.ORDER_CANCEL_WITH_RECEIVED

    def test_close_from_partial_received_allowed(self) -> None:
        order = _sent_order()
        line = order.lines[0]
        order.receive(line.line_id, 3.0)
        assert order.status == PurchaseOrderStatus.PARTIAL_RECEIVED
        order.close()
        assert order.status == PurchaseOrderStatus.CLOSED

    def test_close_from_sent_rejected(self) -> None:
        order = _sent_order()
        with pytest.raises(PURError) as exc:
            order.close()
        assert exc.value.code == PURErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_is_fully_received_line_property(self) -> None:
        line = PurchaseOrderLine(ordered_quantity=10, unit_price=5)
        assert line.is_fully_received is False
        line.received_quantity = 10
        assert line.is_fully_received is True
        assert line.line_amount == 50.0

    def test_is_sent_or_later_covers_downstream_states(self) -> None:
        order = _sent_order()
        assert order.is_sent_or_later is True
        order.change()
        assert order.is_sent_or_later is True

    def test_receive_in_approved_state_silently_accumulates_without_transition(self) -> None:
        # APPROVED 状态下 receive 既未全收、也不在 SENT/CHANGED/PARTIAL_RECEIVED 中，
        # 故仅累加 received_quantity，不触发状态流转（守卫：未发送不进入收货态）。
        order = _submitted_order()
        order.approve(uuid4())
        line = order.lines[0]
        order.receive(line.line_id, 1.0)
        assert order.status == PurchaseOrderStatus.APPROVED
        assert line.received_quantity == 1.0

    def test_cancel_from_rejected_terminal_rejected(self) -> None:
        order = _submitted_order()
        order.reject()
        with pytest.raises(PURError) as exc:
            order.cancel()
        assert exc.value.code == PURErrorCode.ORDER_INVALID_STATE_TRANSITION