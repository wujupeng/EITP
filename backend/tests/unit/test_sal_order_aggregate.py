"""SAL SalesOrderAggregate + PartialFulfillmentService 单元测试 - 订单状态机 + 四态守恒 + 部分发货。

覆盖 DRAFT→SUBMITTED→APPROVED→RESERVED→PARTIAL_SHIPPED→SHIPPED→COMPLETED→CLOSED 主路径、
REJECTED/CANCELLED 终态、四态守恒不变量、add_line 正数校验、部分发货 100→30→40→30 黄金路径、超发拒绝。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.sales.aggregates.sales_order_aggregate import SalesOrderAggregate
from app.domain.sales.entities.sales_order_line import SalesOrderLine
from app.domain.sales.services.partial_fulfillment_service import PartialFulfillmentService
from app.domain.sales.value_objects.sales_order_vo import (
    FourStateQty,
    SalesOrderLineStatus,
    SalesOrderStatus,
)
from app.interfaces.middleware.error_handler import SALError, SALErrorCode


def _line(qty: float = 100.0, price: float = 10.0) -> SalesOrderLine:
    return SalesOrderLine(ordered_quantity=qty, unit_price=price)


def _submitted_order() -> SalesOrderAggregate:
    order = SalesOrderAggregate(order_code="SO-001", idempotency_key="idem-001")
    order.add_line(_line())
    order.submit(uuid4())
    return order


def _reserved_order() -> SalesOrderAggregate:
    order = _submitted_order()
    order.approve(uuid4())
    order.confirm_fulfillment([str(uuid4())])
    return order


class SalesOrderAggregateTest:
    """SalesOrderAggregate 销售订单状态机与四态守恒测试。"""

    def test_default_status_is_draft(self) -> None:
        order = SalesOrderAggregate()
        assert order.status == SalesOrderStatus.DRAFT
        assert order.total_amount == 0.0
        assert order.is_reserved_or_later is False

    def test_add_line_accumulates_total_and_line_number(self) -> None:
        order = SalesOrderAggregate()
        order.add_line(SalesOrderLine(ordered_quantity=10, unit_price=100))
        order.add_line(SalesOrderLine(ordered_quantity=5, unit_price=20))
        assert order.total_amount == 1100.0
        assert order.lines[0].line_number == 1
        assert order.lines[1].line_number == 2

    def test_add_line_non_positive_quantity_rejected(self) -> None:
        with pytest.raises(SALError) as exc:
            SalesOrderLine(ordered_quantity=0, unit_price=10)
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_add_line_non_positive_price_rejected(self) -> None:
        with pytest.raises(SALError) as exc:
            SalesOrderLine(ordered_quantity=10, unit_price=0)
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_submit_without_lines_rejected(self) -> None:
        order = SalesOrderAggregate(idempotency_key="idem-001")
        with pytest.raises(SALError) as exc:
            order.submit(uuid4())
        assert exc.value.code == SALErrorCode.ORDER_NOT_FOUND

    def test_submit_without_idempotency_key_rejected(self) -> None:
        order = SalesOrderAggregate(order_code="SO-001")
        order.add_line(_line())
        with pytest.raises(SALError) as exc:
            order.submit(uuid4())
        assert exc.value.code == SALErrorCode.IDEMPOTENCY_KEY_REQUIRED

    def test_submit_transitions_to_submitted(self) -> None:
        order = _submitted_order()
        assert order.status == SalesOrderStatus.SUBMITTED
        assert order.submitted_at is not None

    def test_approve_sets_approved_by(self) -> None:
        order = _submitted_order()
        approver = uuid4()
        order.approve(approver)
        assert order.status == SalesOrderStatus.APPROVED
        assert order.approved_by == approver

    def test_confirm_fulfillment_requires_reservation_ids(self) -> None:
        order = _submitted_order()
        order.approve(uuid4())
        with pytest.raises(SALError) as exc:
            order.confirm_fulfillment([])
        assert exc.value.code == SALErrorCode.RESERVATION_FAILED

    def test_confirm_fulfillment_transitions_to_reserved(self) -> None:
        order = _reserved_order()
        assert order.status == SalesOrderStatus.RESERVED
        assert order.is_reserved_or_later is True
        assert order.lines[0].status == SalesOrderLineStatus.RESERVED
        assert order.lines[0].reserved_quantity == 100.0

    def test_reject_from_submitted_terminal(self) -> None:
        order = _submitted_order()
        order.reject(uuid4())
        assert order.status == SalesOrderStatus.REJECTED
        with pytest.raises(SALError) as exc:
            order.approve(uuid4())
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_confirm_fulfillment_from_non_approved_rejected(self) -> None:
        order = _submitted_order()
        with pytest.raises(SALError) as exc:
            order.confirm_fulfillment([str(uuid4())])
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_partial_fulfillment_golden_path_100_30_40_30(self) -> None:
        order = _reserved_order()
        line = order.lines[0]
        # 100 → 发 30
        order.update_shipped_quantity(line.line_id, 30.0)
        assert order.status == SalesOrderStatus.PARTIAL_SHIPPED
        assert line.shipped_quantity == 30.0
        assert line.remaining_quantity == 70.0
        # → 发 40
        order.update_shipped_quantity(line.line_id, 40.0)
        assert order.status == SalesOrderStatus.PARTIAL_SHIPPED
        assert line.shipped_quantity == 70.0
        assert line.remaining_quantity == 30.0
        # → 发 30，全发完
        order.update_shipped_quantity(line.line_id, 30.0)
        assert order.status == SalesOrderStatus.SHIPPED
        assert line.shipped_quantity == 100.0
        assert line.remaining_quantity == 0.0
        assert line.is_fully_shipped is True

    def test_ship_in_one_go_transitions_to_shipped(self) -> None:
        order = _reserved_order()
        line = order.lines[0]
        order.update_shipped_quantity(line.line_id, 100.0)
        assert order.status == SalesOrderStatus.SHIPPED

    def test_ship_from_non_reserved_rejected(self) -> None:
        order = _submitted_order()
        order.approve(uuid4())
        line = order.lines[0]
        with pytest.raises(SALError) as exc:
            order.update_shipped_quantity(line.line_id, 10.0)
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_ship_unknown_line_rejected(self) -> None:
        order = _reserved_order()
        with pytest.raises(SALError) as exc:
            order.update_shipped_quantity(uuid4(), 10.0)
        assert exc.value.code == SALErrorCode.ORDER_NOT_FOUND

    def test_over_ship_rejected(self) -> None:
        order = _reserved_order()
        line = order.lines[0]
        order.update_shipped_quantity(line.line_id, 80.0)
        with pytest.raises(SALError) as exc:
            order.update_shipped_quantity(line.line_id, 30.0)  # 80+30 > 100
        assert exc.value.code == SALErrorCode.SHIPMENT_OVER_SHIPPED

    def test_ship_non_positive_quantity_rejected(self) -> None:
        order = _reserved_order()
        line = order.lines[0]
        with pytest.raises(SALError) as exc:
            order.update_shipped_quantity(line.line_id, 0.0)
        assert exc.value.code == SALErrorCode.SHIPMENT_OVER_SHIPPED

    def test_full_lifecycle_to_closed(self) -> None:
        order = _reserved_order()
        line = order.lines[0]
        order.update_shipped_quantity(line.line_id, 100.0)
        assert order.status == SalesOrderStatus.SHIPPED
        order.mark_completed()
        assert order.status == SalesOrderStatus.COMPLETED
        order.close()
        assert order.status == SalesOrderStatus.CLOSED
        assert order.is_reserved_or_later is True

    def test_change_increments_version(self) -> None:
        order = _reserved_order()
        v0 = order.version
        order.change({"expected_delivery_date": "2026-01-01"})
        assert order.version == v0 + 1

    def test_change_from_non_reserved_rejected(self) -> None:
        order = _submitted_order()
        with pytest.raises(SALError) as exc:
            order.change({})
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_cancel_from_draft(self) -> None:
        order = SalesOrderAggregate(order_code="SO-001", idempotency_key="idem-001")
        order.add_line(_line())
        order.cancel()
        assert order.status == SalesOrderStatus.CANCELLED

    def test_cancel_from_reserved_releases_reservation(self) -> None:
        order = _reserved_order()
        line = order.lines[0]
        assert line.reservation_id is not None
        order.cancel()
        assert order.status == SalesOrderStatus.CANCELLED
        assert line.reservation_id is None
        assert line.reserved_quantity == 0.0

    def test_cancel_with_shipped_rejected(self) -> None:
        order = _reserved_order()
        line = order.lines[0]
        order.update_shipped_quantity(line.line_id, 30.0)
        with pytest.raises(SALError) as exc:
            order.cancel()
        assert exc.value.code == SALErrorCode.ORDER_CANCEL_WITH_SHIPPED

    def test_close_from_non_completed_rejected(self) -> None:
        order = _reserved_order()
        with pytest.raises(SALError) as exc:
            order.close()
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_has_shipped_property(self) -> None:
        order = _reserved_order()
        assert order.has_shipped is False
        line = order.lines[0]
        order.update_shipped_quantity(line.line_id, 30.0)
        assert order.has_shipped is True


class SalesOrderLineTest:
    """SalesOrderLine 四态守恒与行级操作测试。"""

    def test_remaining_quantity_calculation(self) -> None:
        line = _line(qty=100, price=10)
        assert line.remaining_quantity == 100.0
        line.shipped_quantity = 40
        assert line.remaining_quantity == 60.0

    def test_line_amount_calculation(self) -> None:
        line = SalesOrderLine(ordered_quantity=10, unit_price=7.5)
        assert line.line_amount == 75.0

    def test_mark_reserved_sets_reservation(self) -> None:
        line = _line()
        rid = uuid4()
        line.mark_reserved(rid)
        assert line.reservation_id == rid
        assert line.reserved_quantity == 100.0
        assert line.status == SalesOrderLineStatus.RESERVED

    def test_mark_reserved_twice_rejected(self) -> None:
        line = _line()
        line.mark_reserved(uuid4())
        with pytest.raises(SALError) as exc:
            line.mark_reserved(uuid4())
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_ship_partial_sets_partial_status(self) -> None:
        line = _line()
        line.mark_reserved(uuid4())
        line.ship(40.0)
        assert line.shipped_quantity == 40.0
        assert line.status == SalesOrderLineStatus.PARTIAL_SHIPPED
        assert line.is_partial_shipped is True

    def test_ship_full_sets_shipped_status(self) -> None:
        line = _line()
        line.mark_reserved(uuid4())
        line.ship(100.0)
        assert line.status == SalesOrderLineStatus.SHIPPED
        assert line.is_fully_shipped is True

    def test_ship_over_ordered_rejected(self) -> None:
        line = _line()
        line.mark_reserved(uuid4())
        with pytest.raises(SALError) as exc:
            line.ship(101.0)
        assert exc.value.code == SALErrorCode.SHIPMENT_OVER_SHIPPED

    def test_release_reservation_when_not_shipped(self) -> None:
        line = _line()
        line.mark_reserved(uuid4())
        line.release_reservation()
        assert line.reservation_id is None
        assert line.reserved_quantity == 0.0
        assert line.status == SalesOrderLineStatus.OPEN

    def test_release_reservation_when_shipped_rejected(self) -> None:
        line = _line()
        line.mark_reserved(uuid4())
        line.ship(30.0)
        with pytest.raises(SALError) as exc:
            line.release_reservation()
        assert exc.value.code == SALErrorCode.ORDER_CANCEL_WITH_SHIPPED

    def test_cancel_line_when_shipped_rejected(self) -> None:
        line = _line()
        line.mark_reserved(uuid4())
        line.ship(30.0)
        with pytest.raises(SALError) as exc:
            line.cancel()
        assert exc.value.code == SALErrorCode.ORDER_CANCEL_WITH_SHIPPED

    def test_cancel_line_when_not_shipped(self) -> None:
        line = _line()
        line.mark_reserved(uuid4())
        line.cancel()
        assert line.status == SalesOrderLineStatus.CANCELLED
        assert line.reservation_id is None
        assert line.reserved_quantity == 0.0


class FourStateQtyTest:
    """FourStateQty 四态守恒不变量测试。"""

    def test_create_initial_state(self) -> None:
        fs = FourStateQty.create(100.0)
        assert fs.ordered == 100.0
        assert fs.reserved == 0.0
        assert fs.shipped == 0.0
        assert fs.remaining == 100.0

    def test_invariant_violation_remaining_mismatch_rejected(self) -> None:
        with pytest.raises(SALError) as exc:
            FourStateQty(ordered=100, reserved=0, shipped=30, remaining=50)
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_reserved_over_ordered_rejected(self) -> None:
        with pytest.raises(SALError) as exc:
            FourStateQty(ordered=100, reserved=120, shipped=0, remaining=100)
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_shipped_over_ordered_rejected(self) -> None:
        with pytest.raises(SALError) as exc:
            FourStateQty(ordered=100, reserved=100, shipped=120, remaining=-20)
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_shipped_over_reserved_rejected(self) -> None:
        with pytest.raises(SALError) as exc:
            FourStateQty(ordered=100, reserved=30, shipped=40, remaining=60)
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_negative_ordered_rejected(self) -> None:
        with pytest.raises(SALError) as exc:
            FourStateQty(ordered=-1, reserved=0, shipped=0, remaining=-1)
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_negative_reserved_or_shipped_rejected(self) -> None:
        with pytest.raises(SALError) as exc:
            FourStateQty(ordered=100, reserved=-1, shipped=0, remaining=100)
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION
        with pytest.raises(SALError) as exc:
            FourStateQty(ordered=100, reserved=0, shipped=-1, remaining=101)
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_with_reserved_returns_new_instance(self) -> None:
        # with_reserved 保留当前 shipped/remaining；在已全发场景（remaining=0）下合法。
        fs = FourStateQty(ordered=100, reserved=100, shipped=100, remaining=0)
        fs2 = fs.with_reserved(100.0)
        assert fs2.reserved == 100.0
        assert fs2.shipped == 100.0
        assert fs2.remaining == 0.0

    def test_with_shipped_returns_new_instance(self) -> None:
        fs = FourStateQty(ordered=100, reserved=100, shipped=0, remaining=100)
        fs2 = fs.with_shipped(40.0)
        assert fs2.shipped == 40.0
        assert fs2.remaining == 60.0
        assert fs2.reserved == 100.0


class PartialFulfillmentServiceTest:
    """PartialFulfillmentService 部分发货与四态守恒校验测试。"""

    def test_validate_and_ship_returns_four_state(self) -> None:
        line = _line()
        line.mark_reserved(uuid4())
        fs = PartialFulfillmentService.validate_and_ship(line, 30.0)
        assert fs.ordered == 100.0
        assert fs.shipped == 30.0
        assert fs.remaining == 70.0

    def test_validate_and_ship_non_positive_rejected(self) -> None:
        line = _line()
        line.mark_reserved(uuid4())
        with pytest.raises(SALError) as exc:
            PartialFulfillmentService.validate_and_ship(line, 0.0)
        assert exc.value.code == SALErrorCode.SHIPMENT_OVER_SHIPPED

    def test_validate_and_ship_over_remaining_rejected(self) -> None:
        line = _line()
        line.mark_reserved(uuid4())
        line.ship(80.0)
        with pytest.raises(SALError) as exc:
            PartialFulfillmentService.validate_and_ship(line, 30.0)  # 80+30 > 100
        assert exc.value.code == SALErrorCode.SHIPMENT_OVER_SHIPPED

    def test_apply_to_order_links_state(self) -> None:
        order = _reserved_order()
        line = order.lines[0]
        PartialFulfillmentService.apply_to_order(order, line.line_id, 50.0)
        assert order.status == SalesOrderStatus.PARTIAL_SHIPPED
        assert line.shipped_quantity == 50.0

    def test_verify_four_state_invariant_passes_for_valid_order(self) -> None:
        order = _reserved_order()
        line = order.lines[0]
        order.update_shipped_quantity(line.line_id, 30.0)
        # 不抛异常即通过
        PartialFulfillmentService.verify_four_state_invariant(order)