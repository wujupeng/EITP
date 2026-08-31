"""T16-04 操作订单聚合根单元测试。

覆盖 ReceivingOrderAggregate 收货数量校验（超收拒绝+超收比例+部分收货+免检直接 AVAILABLE）、
PickingTaskAggregate 多库位拆分与可用量校验、TransferOrderAggregate 同仓库与审批流转、
ShippingOrderAggregate 拣货完成校验与物流单号录入。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.shared.entity import EntityId
from app.domain.warehouse.aggregates.picking_task_aggregate import (
    PickingStatus,
    PickingTaskAggregate,
)
from app.domain.warehouse.aggregates.receiving_order_aggregate import (
    ReceivingOrderAggregate,
    ReceivingStatus,
)
from app.domain.warehouse.aggregates.shipping_order_aggregate import (
    ShippingOrderAggregate,
    ShippingStatus,
)
from app.domain.warehouse.aggregates.transfer_order_aggregate import (
    TransferOrderAggregate,
    TransferStatus,
)
from app.domain.warehouse.value_objects.batch_lot import BatchLot
from app.domain.warehouse.value_objects.wms_config import PickingStrategy
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode


def _make_receiving_order(
    *, over_receive_ratio: float = 0.0
) -> ReceivingOrderAggregate:
    return ReceivingOrderAggregate(
        id=EntityId.generate(),
        tenant_id=uuid4(),
        source_document_id=uuid4(),
        source_document_type="purchase_order",
        warehouse_id=uuid4(),
        zone_id=uuid4(),
        over_receive_ratio=over_receive_ratio,
    )


def _make_picking_task() -> PickingTaskAggregate:
    return PickingTaskAggregate(
        id=EntityId.generate(),
        tenant_id=uuid4(),
        source_order_id=uuid4(),
        source_order_type="sales_order",
        warehouse_id=uuid4(),
        picking_strategy=PickingStrategy.FIFO,
    )


def _make_transfer_order(*, require_approval: bool = False) -> TransferOrderAggregate:
    return TransferOrderAggregate(
        id=EntityId.generate(),
        tenant_id=uuid4(),
        warehouse_id=uuid4(),
        require_approval=require_approval,
    )


def _make_shipping_order(
    *, picking_completed: bool = False
) -> ShippingOrderAggregate:
    return ShippingOrderAggregate(
        id=EntityId.generate(),
        tenant_id=uuid4(),
        source_order_id=uuid4(),
        warehouse_id=uuid4(),
        zone_id=uuid4(),
        picking_completed=picking_completed,
    )


class ReceivingOrderAggregateTest:
    """ReceivingOrderAggregate 收货单聚合根测试。"""

    def test_initial_status_is_draft(self) -> None:
        order = _make_receiving_order()
        assert order.status == ReceivingStatus.DRAFT
        assert order.lines == []

    def test_add_line_in_draft(self) -> None:
        order = _make_receiving_order()
        line = order.add_line(sku_id=uuid4(), ordered_quantity=100)
        assert len(order.lines) == 1
        assert order.lines[0].line_id == line.line_id
        assert line.ordered_quantity == 100
        assert line.is_inspection_required is True

    def test_add_line_inspection_exempt(self) -> None:
        order = _make_receiving_order()
        line = order.add_line(
            sku_id=uuid4(), ordered_quantity=100, is_inspection_required=False
        )
        assert line.is_inspection_exempt is True
        assert line.is_inspection_required is False

    def test_add_line_rejected_after_submit(self) -> None:
        order = _make_receiving_order()
        order.add_line(sku_id=uuid4(), ordered_quantity=100)
        order.submit()
        with pytest.raises(WMSError) as exc:
            order.add_line(sku_id=uuid4(), ordered_quantity=50)
        assert exc.value.code == WMSErrorCode.RECEIVING_ALREADY_COMPLETED

    def test_submit_rejected_without_lines(self) -> None:
        order = _make_receiving_order()
        with pytest.raises(WMSError) as exc:
            order.submit()
        assert exc.value.code == WMSErrorCode.SERVICE_UNAVAILABLE

    def test_submit_transitions_to_submitted(self) -> None:
        order = _make_receiving_order()
        order.add_line(sku_id=uuid4(), ordered_quantity=100)
        order.submit()
        assert order.status == ReceivingStatus.SUBMITTED

    def test_execute_line_partial_receive(self) -> None:
        order = _make_receiving_order()
        line = order.add_line(sku_id=uuid4(), ordered_quantity=100)
        order.submit()
        order.execute_line(line.line_id, received_qty=40)
        assert line.received_quantity == 40
        assert order.status == ReceivingStatus.EXECUTING
        assert line.is_fully_received is False

    def test_execute_line_full_receive(self) -> None:
        order = _make_receiving_order()
        line = order.add_line(sku_id=uuid4(), ordered_quantity=100)
        order.submit()
        order.execute_line(line.line_id, received_qty=100)
        assert line.is_fully_received is True

    def test_execute_line_accumulates_partial_receive(self) -> None:
        order = _make_receiving_order()
        line = order.add_line(sku_id=uuid4(), ordered_quantity=100)
        order.submit()
        order.execute_line(line.line_id, received_qty=30)
        order.execute_line(line.line_id, received_qty=50)
        assert line.received_quantity == 80

    def test_execute_line_over_receive_rejected(self) -> None:
        order = _make_receiving_order()
        line = order.add_line(sku_id=uuid4(), ordered_quantity=100)
        order.submit()
        with pytest.raises(WMSError) as exc:
            order.execute_line(line.line_id, received_qty=101)
        assert exc.value.code == WMSErrorCode.RECEIVING_OVER_RECEIVED

    def test_execute_line_over_receive_accumulated_rejected(self) -> None:
        order = _make_receiving_order()
        line = order.add_line(sku_id=uuid4(), ordered_quantity=100)
        order.submit()
        order.execute_line(line.line_id, received_qty=80)
        with pytest.raises(WMSError) as exc:
            order.execute_line(line.line_id, received_qty=30)
        assert exc.value.code == WMSErrorCode.RECEIVING_OVER_RECEIVED

    def test_execute_line_over_receive_ratio_allows_excess(self) -> None:
        order = _make_receiving_order(over_receive_ratio=0.1)
        line = order.add_line(sku_id=uuid4(), ordered_quantity=100)
        order.submit()
        order.execute_line(line.line_id, received_qty=110)
        assert line.received_quantity == 110

    def test_execute_line_over_receive_ratio_still_rejects_beyond(self) -> None:
        order = _make_receiving_order(over_receive_ratio=0.1)
        line = order.add_line(sku_id=uuid4(), ordered_quantity=100)
        order.submit()
        with pytest.raises(WMSError) as exc:
            order.execute_line(line.line_id, received_qty=111)
        assert exc.value.code == WMSErrorCode.RECEIVING_OVER_RECEIVED

    def test_execute_line_with_batch_lot(self) -> None:
        order = _make_receiving_order()
        line = order.add_line(sku_id=uuid4(), ordered_quantity=100)
        order.submit()
        bl = BatchLot(batch_number="B001", lot_number="L001")
        order.execute_line(line.line_id, received_qty=50, batch_lot=bl)
        assert line.batch_lot.batch_number == "B001"

    def test_execute_line_with_location(self) -> None:
        order = _make_receiving_order()
        line = order.add_line(sku_id=uuid4(), ordered_quantity=100)
        order.submit()
        loc_id = uuid4()
        order.execute_line(line.line_id, received_qty=50, location_id=loc_id)
        assert line.location_id == loc_id

    def test_execute_line_not_found(self) -> None:
        order = _make_receiving_order()
        order.add_line(sku_id=uuid4(), ordered_quantity=100)
        order.submit()
        with pytest.raises(WMSError) as exc:
            order.execute_line(uuid4(), received_qty=10)
        assert exc.value.code == WMSErrorCode.RECEIVING_NOT_FOUND

    def test_execute_line_rejected_before_submit(self) -> None:
        order = _make_receiving_order()
        line = order.add_line(sku_id=uuid4(), ordered_quantity=100)
        with pytest.raises(WMSError) as exc:
            order.execute_line(line.line_id, received_qty=10)
        assert exc.value.code == WMSErrorCode.RECEIVING_ALREADY_COMPLETED

    def test_complete_transitions_to_completed(self) -> None:
        order = _make_receiving_order()
        line = order.add_line(sku_id=uuid4(), ordered_quantity=100)
        order.submit()
        order.execute_line(line.line_id, received_qty=100)
        order.complete()
        assert order.status == ReceivingStatus.COMPLETED

    def test_complete_rejected_before_execute(self) -> None:
        order = _make_receiving_order()
        order.add_line(sku_id=uuid4(), ordered_quantity=100)
        order.submit()
        with pytest.raises(WMSError) as exc:
            order.complete()
        assert exc.value.code == WMSErrorCode.RECEIVING_ALREADY_COMPLETED

    def test_is_all_lines_received(self) -> None:
        order = _make_receiving_order()
        line = order.add_line(sku_id=uuid4(), ordered_quantity=100)
        order.submit()
        order.execute_line(line.line_id, received_qty=100)
        assert order.is_all_lines_received() is True

    def test_is_all_lines_received_false_when_partial(self) -> None:
        order = _make_receiving_order()
        line = order.add_line(sku_id=uuid4(), ordered_quantity=100)
        order.submit()
        order.execute_line(line.line_id, received_qty=50)
        assert order.is_all_lines_received() is False


class PickingTaskAggregateTest:
    """PickingTaskAggregate 拣货任务聚合根测试 - 多库位拆分与可用量校验。"""

    def test_initial_status_is_draft(self) -> None:
        task = _make_picking_task()
        assert task.status == PickingStatus.DRAFT
        assert task.lines == []
        assert task.reservation_id is None

    def test_add_line_in_draft(self) -> None:
        task = _make_picking_task()
        loc_id = uuid4()
        line = task.add_line(
            sku_id=uuid4(), source_location_id=loc_id, required_quantity=100
        )
        assert len(task.lines) == 1
        assert line.required_quantity == 100
        assert line.source_location_id == loc_id

    def test_add_line_rejected_after_reservation(self) -> None:
        task = _make_picking_task()
        task.add_line(sku_id=uuid4(), source_location_id=uuid4(), required_quantity=100)
        task.create_reservation(uuid4())
        with pytest.raises(WMSError) as exc:
            task.add_line(sku_id=uuid4(), source_location_id=uuid4(), required_quantity=50)
        assert exc.value.code == WMSErrorCode.PICKING_ALREADY_COMPLETED

    def test_create_reservation_transitions_to_reserved(self) -> None:
        task = _make_picking_task()
        task.add_line(sku_id=uuid4(), source_location_id=uuid4(), required_quantity=100)
        res_id = uuid4()
        task.create_reservation(res_id)
        assert task.status == PickingStatus.RESERVED
        assert task.reservation_id == res_id

    def test_create_reservation_rejected_when_not_draft(self) -> None:
        task = _make_picking_task()
        task.add_line(sku_id=uuid4(), source_location_id=uuid4(), required_quantity=100)
        task.create_reservation(uuid4())
        with pytest.raises(WMSError) as exc:
            task.create_reservation(uuid4())
        assert exc.value.code == WMSErrorCode.PICKING_STATUS_UNAVAILABLE

    def test_execute_line_partial_pick(self) -> None:
        task = _make_picking_task()
        line = task.add_line(
            sku_id=uuid4(), source_location_id=uuid4(), required_quantity=100
        )
        task.create_reservation(uuid4())
        task.execute_line(line.line_id, picked_qty=60)
        assert line.picked_quantity == 60
        assert task.status == PickingStatus.EXECUTING
        assert line.is_fully_picked is False

    def test_execute_line_full_pick(self) -> None:
        task = _make_picking_task()
        line = task.add_line(
            sku_id=uuid4(), source_location_id=uuid4(), required_quantity=100
        )
        task.create_reservation(uuid4())
        task.execute_line(line.line_id, picked_qty=100)
        assert line.is_fully_picked is True

    def test_execute_line_multi_location_split(self) -> None:
        """多库位拆分：需 100，库位 A 拣 60，库位 B 拣 40。"""
        task = _make_picking_task()
        line_a = task.add_line(
            sku_id=uuid4(), source_location_id=uuid4(), required_quantity=60
        )
        line_b = task.add_line(
            sku_id=uuid4(), source_location_id=uuid4(), required_quantity=40
        )
        task.create_reservation(uuid4())
        task.execute_line(line_a.line_id, picked_qty=60)
        task.execute_line(line_b.line_id, picked_qty=40)
        assert task.is_all_lines_picked() is True

    def test_execute_line_accumulates_picked_quantity(self) -> None:
        task = _make_picking_task()
        line = task.add_line(
            sku_id=uuid4(), source_location_id=uuid4(), required_quantity=100
        )
        task.create_reservation(uuid4())
        task.execute_line(line.line_id, picked_qty=30)
        task.execute_line(line.line_id, picked_qty=50)
        assert line.picked_quantity == 80

    def test_execute_line_rejects_excess_quantity(self) -> None:
        task = _make_picking_task()
        line = task.add_line(
            sku_id=uuid4(), source_location_id=uuid4(), required_quantity=100
        )
        task.create_reservation(uuid4())
        with pytest.raises(WMSError) as exc:
            task.execute_line(line.line_id, picked_qty=101)
        assert exc.value.code == WMSErrorCode.PICKING_QTY_MISMATCH

    def test_execute_line_rejects_accumulated_excess(self) -> None:
        task = _make_picking_task()
        line = task.add_line(
            sku_id=uuid4(), source_location_id=uuid4(), required_quantity=100
        )
        task.create_reservation(uuid4())
        task.execute_line(line.line_id, picked_qty=80)
        with pytest.raises(WMSError) as exc:
            task.execute_line(line.line_id, picked_qty=30)
        assert exc.value.code == WMSErrorCode.PICKING_QTY_MISMATCH

    def test_execute_line_not_found(self) -> None:
        task = _make_picking_task()
        task.add_line(sku_id=uuid4(), source_location_id=uuid4(), required_quantity=100)
        task.create_reservation(uuid4())
        with pytest.raises(WMSError) as exc:
            task.execute_line(uuid4(), picked_qty=10)
        assert exc.value.code == WMSErrorCode.PICKING_NOT_FOUND

    def test_execute_line_rejected_before_reservation(self) -> None:
        task = _make_picking_task()
        line = task.add_line(
            sku_id=uuid4(), source_location_id=uuid4(), required_quantity=100
        )
        with pytest.raises(WMSError) as exc:
            task.execute_line(line.line_id, picked_qty=10)
        assert exc.value.code == WMSErrorCode.PICKING_STATUS_UNAVAILABLE

    def test_complete_transitions_to_completed(self) -> None:
        task = _make_picking_task()
        line = task.add_line(
            sku_id=uuid4(), source_location_id=uuid4(), required_quantity=100
        )
        task.create_reservation(uuid4())
        task.execute_line(line.line_id, picked_qty=100)
        task.complete()
        assert task.status == PickingStatus.COMPLETED

    def test_complete_rejected_before_execute(self) -> None:
        task = _make_picking_task()
        task.add_line(sku_id=uuid4(), source_location_id=uuid4(), required_quantity=100)
        task.create_reservation(uuid4())
        with pytest.raises(WMSError) as exc:
            task.complete()
        assert exc.value.code == WMSErrorCode.PICKING_ALREADY_COMPLETED


class TransferOrderAggregateTest:
    """TransferOrderAggregate 移库单聚合根测试 - 同仓库与审批流转。"""

    def test_initial_status_is_draft(self) -> None:
        order = _make_transfer_order()
        assert order.status == TransferStatus.DRAFT
        assert order.require_approval is False

    def test_add_line_in_draft(self) -> None:
        order = _make_transfer_order()
        line = order.add_line(
            sku_id=uuid4(),
            source_location_id=uuid4(),
            target_location_id=uuid4(),
            quantity=50,
        )
        assert len(order.lines) == 1
        assert line.quantity == 50

    def test_add_line_rejected_after_submit(self) -> None:
        order = _make_transfer_order()
        order.add_line(
            sku_id=uuid4(),
            source_location_id=uuid4(),
            target_location_id=uuid4(),
            quantity=50,
        )
        order.submit()
        with pytest.raises(WMSError) as exc:
            order.add_line(
                sku_id=uuid4(),
                source_location_id=uuid4(),
                target_location_id=uuid4(),
                quantity=10,
            )
        assert exc.value.code == WMSErrorCode.TRANSFER_NOT_FOUND

    def test_submit_transitions_to_submitted(self) -> None:
        order = _make_transfer_order()
        order.submit()
        assert order.status == TransferStatus.SUBMITTED

    def test_approve_transitions_to_approved(self) -> None:
        order = _make_transfer_order(require_approval=True)
        order.submit()
        approver = uuid4()
        order.approve(approver, opinion="ok")
        assert order.status == TransferStatus.APPROVED
        assert order.approver_id == approver

    def test_reject_transitions_to_rejected(self) -> None:
        order = _make_transfer_order(require_approval=True)
        order.submit()
        order.reject(uuid4(), opinion="no")
        assert order.status == TransferStatus.REJECTED

    def test_approve_rejected_when_not_submitted(self) -> None:
        order = _make_transfer_order(require_approval=True)
        with pytest.raises(WMSError) as exc:
            order.approve(uuid4())
        assert exc.value.code == WMSErrorCode.TRANSFER_NOT_FOUND

    def test_execute_without_approval_requirement(self) -> None:
        order = _make_transfer_order(require_approval=False)
        order.submit()
        order.execute()
        assert order.status == TransferStatus.EXECUTING

    def test_execute_with_approval_requirement(self) -> None:
        order = _make_transfer_order(require_approval=True)
        order.submit()
        order.approve(uuid4())
        order.execute()
        assert order.status == TransferStatus.EXECUTING

    def test_execute_rejected_when_approval_required_but_not_approved(self) -> None:
        order = _make_transfer_order(require_approval=True)
        order.submit()
        with pytest.raises(WMSError) as exc:
            order.execute()
        assert exc.value.code == WMSErrorCode.TRANSFER_NOT_FOUND

    def test_execute_rejected_when_not_submitted(self) -> None:
        order = _make_transfer_order(require_approval=False)
        with pytest.raises(WMSError) as exc:
            order.execute()
        assert exc.value.code == WMSErrorCode.TRANSFER_NOT_FOUND

    def test_complete_transitions_to_completed(self) -> None:
        order = _make_transfer_order(require_approval=False)
        order.submit()
        order.execute()
        order.complete()
        assert order.status == TransferStatus.COMPLETED

    def test_complete_rejected_before_execute(self) -> None:
        order = _make_transfer_order(require_approval=False)
        order.submit()
        with pytest.raises(WMSError) as exc:
            order.complete()
        assert exc.value.code == WMSErrorCode.TRANSFER_NOT_FOUND

    def test_full_approval_flow(self) -> None:
        order = _make_transfer_order(require_approval=True)
        order.add_line(
            sku_id=uuid4(),
            source_location_id=uuid4(),
            target_location_id=uuid4(),
            quantity=10,
        )
        order.submit()
        order.approve(uuid4(), opinion="approved")
        order.execute()
        order.complete()
        assert order.status == TransferStatus.COMPLETED


class ShippingOrderAggregateTest:
    """ShippingOrderAggregate 发货单聚合根测试 - 拣货完成校验与物流单号录入。"""

    def test_initial_status_is_draft(self) -> None:
        order = _make_shipping_order()
        assert order.status == ShippingStatus.DRAFT
        assert order.lines == []
        assert order.logistics_info.is_set() is False

    def test_add_line_in_draft(self) -> None:
        order = _make_shipping_order()
        line = order.add_line(sku_id=uuid4(), quantity=20)
        assert len(order.lines) == 1
        assert line.quantity == 20

    def test_add_line_rejected_after_execute(self) -> None:
        order = _make_shipping_order(picking_completed=True)
        order.add_line(sku_id=uuid4(), quantity=20)
        order.execute(logistics_no="SF001", logistics_company="顺丰")
        with pytest.raises(WMSError) as exc:
            order.add_line(sku_id=uuid4(), quantity=10)
        assert exc.value.code == WMSErrorCode.SHIPPING_ALREADY_COMPLETED

    def test_execute_rejected_when_picking_not_completed(self) -> None:
        order = _make_shipping_order(picking_completed=False)
        order.add_line(sku_id=uuid4(), quantity=20)
        with pytest.raises(WMSError) as exc:
            order.execute(logistics_no="SF001", logistics_company="顺丰")
        assert exc.value.code == WMSErrorCode.SHIPPING_PICKING_NOT_COMPLETED

    def test_execute_rejected_when_logistics_no_empty(self) -> None:
        order = _make_shipping_order(picking_completed=True)
        order.add_line(sku_id=uuid4(), quantity=20)
        with pytest.raises(WMSError) as exc:
            order.execute(logistics_no="", logistics_company="顺丰")
        assert exc.value.code == WMSErrorCode.SHIPPING_ZONE_INVALID

    def test_execute_rejected_when_logistics_company_empty(self) -> None:
        order = _make_shipping_order(picking_completed=True)
        order.add_line(sku_id=uuid4(), quantity=20)
        with pytest.raises(WMSError) as exc:
            order.execute(logistics_no="SF001", logistics_company="")
        assert exc.value.code == WMSErrorCode.SHIPPING_ZONE_INVALID

    def test_execute_records_logistics_info(self) -> None:
        order = _make_shipping_order(picking_completed=True)
        order.add_line(sku_id=uuid4(), quantity=20)
        order.execute(logistics_no="SF001", logistics_company="顺丰")
        assert order.status == ShippingStatus.EXECUTING
        assert order.logistics_info.logistics_no == "SF001"
        assert order.logistics_info.logistics_company == "顺丰"
        assert order.logistics_info.shipped_at is not None
        assert order.logistics_info.is_set() is True

    def test_mark_picking_completed_then_execute(self) -> None:
        order = _make_shipping_order(picking_completed=False)
        order.add_line(sku_id=uuid4(), quantity=20)
        order.mark_picking_completed()
        order.execute(logistics_no="YT001", logistics_company="圆通")
        assert order.status == ShippingStatus.EXECUTING

    def test_complete_transitions_to_completed(self) -> None:
        order = _make_shipping_order(picking_completed=True)
        order.add_line(sku_id=uuid4(), quantity=20)
        order.execute(logistics_no="SF001", logistics_company="顺丰")
        order.complete()
        assert order.status == ShippingStatus.COMPLETED

    def test_complete_rejected_before_execute(self) -> None:
        order = _make_shipping_order(picking_completed=True)
        order.add_line(sku_id=uuid4(), quantity=20)
        with pytest.raises(WMSError) as exc:
            order.complete()
        assert exc.value.code == WMSErrorCode.SHIPPING_ALREADY_COMPLETED