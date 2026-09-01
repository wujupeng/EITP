"""SAL ShipmentOrderAggregate / PackingRecordAggregate 单元测试 - 发货单状态机 + 包装汇总。

覆盖 DRAFT→SUBMITTED→PICKING→PACKED→SHIPPED→COMPLETED 主路径、CANCELLED/FAILED 终态、
submit 校验、发货数量校验、包装明细汇总（毛重/净重/体积/件数）。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.sales.aggregates.packing_record_aggregate import PackingRecordAggregate
from app.domain.sales.aggregates.shipment_order_aggregate import ShipmentOrderAggregate
from app.domain.sales.entities.packing_line import PackingLine
from app.domain.sales.entities.shipment_line import ShipmentLine
from app.domain.sales.value_objects.shipment_vo import PackingStatus, ShipmentStatus
from app.interfaces.middleware.error_handler import SALError, SALErrorCode


def _ship_line(qty: float = 10.0) -> ShipmentLine:
    return ShipmentLine(ship_quantity=qty)


def _submitted_shipment() -> ShipmentOrderAggregate:
    s = ShipmentOrderAggregate(
        shipment_code="SH-001",
        order_ids=[str(uuid4())],
        idempotency_key="idem-sh-001",
    )
    s.add_line(_ship_line())
    s.submit()
    return s


def _packed_shipment() -> ShipmentOrderAggregate:
    s = _submitted_shipment()
    s.mark_picking(uuid4())
    s.mark_packed()
    return s


class ShipmentOrderAggregateTest:
    """ShipmentOrderAggregate 发货单状态机测试。"""

    def test_default_status_is_draft(self) -> None:
        s = ShipmentOrderAggregate()
        assert s.status == ShipmentStatus.DRAFT
        assert s.total_ship_quantity == 0.0

    def test_ship_line_non_positive_quantity_rejected(self) -> None:
        with pytest.raises(SALError) as exc:
            ShipmentLine(ship_quantity=0)
        assert exc.value.code == SALErrorCode.SHIPMENT_OVER_SHIPPED

    def test_add_line_accumulates_quantity(self) -> None:
        s = ShipmentOrderAggregate()
        s.add_line(ShipmentLine(ship_quantity=10))
        s.add_line(ShipmentLine(ship_quantity=5))
        assert s.total_ship_quantity == 15.0
        assert len(s.lines) == 2

    def test_submit_without_lines_rejected(self) -> None:
        s = ShipmentOrderAggregate(order_ids=[str(uuid4())], idempotency_key="idem")
        with pytest.raises(SALError) as exc:
            s.submit()
        assert exc.value.code == SALErrorCode.SHIPMENT_NOT_FOUND

    def test_submit_without_order_ids_rejected(self) -> None:
        s = ShipmentOrderAggregate(idempotency_key="idem")
        s.add_line(_ship_line())
        with pytest.raises(SALError) as exc:
            s.submit()
        assert exc.value.code == SALErrorCode.SHIPMENT_NOT_FOUND

    def test_submit_without_idempotency_key_rejected(self) -> None:
        s = ShipmentOrderAggregate(order_ids=[str(uuid4())])
        s.add_line(_ship_line())
        with pytest.raises(SALError) as exc:
            s.submit()
        assert exc.value.code == SALErrorCode.IDEMPOTENCY_KEY_REQUIRED

    def test_submit_transitions_to_submitted(self) -> None:
        s = _submitted_shipment()
        assert s.status == ShipmentStatus.SUBMITTED

    def test_full_lifecycle_to_completed(self) -> None:
        s = _packed_shipment()
        s.confirm("SF-LOG-001", uuid4(), ["inv-tx-1"])
        assert s.status == ShipmentStatus.SHIPPED
        assert s.logistics_no == "SF-LOG-001"
        assert s.shipped_at is not None
        s.complete()
        assert s.status == ShipmentStatus.COMPLETED

    def test_mark_picking_sets_task_id(self) -> None:
        s = _submitted_shipment()
        task_id = uuid4()
        s.mark_picking(task_id)
        assert s.status == ShipmentStatus.PICKING
        assert s.wms_picking_task_id == task_id

    def test_confirm_without_logistics_no_rejected(self) -> None:
        s = _packed_shipment()
        with pytest.raises(SALError) as exc:
            s.confirm("", uuid4(), [])
        assert exc.value.code == SALErrorCode.SHIPMENT_ORDER_INVALID

    def test_confirm_from_non_packed_rejected(self) -> None:
        s = _submitted_shipment()
        s.mark_picking(uuid4())
        with pytest.raises(SALError) as exc:
            s.confirm("LOG-001", uuid4(), [])
        assert exc.value.code == SALErrorCode.SHIPMENT_ORDER_INVALID

    def test_cancel_from_draft(self) -> None:
        s = ShipmentOrderAggregate(shipment_code="SH-002")
        s.add_line(_ship_line())
        s.cancel()
        assert s.status == ShipmentStatus.CANCELLED

    def test_cancel_from_submitted(self) -> None:
        s = _submitted_shipment()
        s.cancel()
        assert s.status == ShipmentStatus.CANCELLED

    def test_cancelled_is_terminal(self) -> None:
        s = _submitted_shipment()
        s.cancel()
        with pytest.raises(SALError) as exc:
            s.mark_picking(uuid4())
        assert exc.value.code == SALErrorCode.SHIPMENT_ORDER_INVALID

    def test_mark_failed_from_picking(self) -> None:
        s = _submitted_shipment()
        s.mark_picking(uuid4())
        s.mark_failed()
        assert s.status == ShipmentStatus.FAILED

    def test_mark_failed_from_shipped_rejected(self) -> None:
        s = _packed_shipment()
        s.confirm("LOG-001", uuid4(), [])
        with pytest.raises(SALError) as exc:
            s.mark_failed()
        assert exc.value.code == SALErrorCode.WMS_SHIPPING_FAILED

    def test_mark_picking_from_draft_rejected(self) -> None:
        s = ShipmentOrderAggregate(shipment_code="SH-003")
        s.add_line(_ship_line())
        with pytest.raises(SALError) as exc:
            s.mark_picking(uuid4())
        assert exc.value.code == SALErrorCode.SHIPMENT_ORDER_INVALID

    def test_complete_from_non_shipped_rejected(self) -> None:
        s = _packed_shipment()
        with pytest.raises(SALError) as exc:
            s.complete()
        assert exc.value.code == SALErrorCode.SHIPMENT_ORDER_INVALID


class PackingRecordAggregateTest:
    """PackingRecordAggregate 包装明细汇总测试。"""

    def test_default_status_is_draft(self) -> None:
        p = PackingRecordAggregate()
        assert p.status == PackingStatus.DRAFT

    def test_add_line_appends(self) -> None:
        p = PackingRecordAggregate()
        p.add_line(PackingLine(quantity=10, carton_no="C1", gross_weight=5.0, net_weight=4.0))
        assert len(p.lines) == 1

    def test_calculate_summary_aggregates_weights_and_volume(self) -> None:
        p = PackingRecordAggregate()
        p.add_line(PackingLine(quantity=10, carton_no="C1", gross_weight=5.0, net_weight=4.0, volume=1.5))
        p.add_line(PackingLine(quantity=8, carton_no="C2", gross_weight=3.0, net_weight=2.5, volume=0.8))
        p.calculate_summary()
        assert p.total_gross_weight == 8.0
        assert p.total_net_weight == 6.5
        assert p.total_volume == 2.3
        assert p.package_count == 2

    def test_calculate_summary_dedupes_carton_no(self) -> None:
        p = PackingRecordAggregate()
        p.add_line(PackingLine(carton_no="C1", gross_weight=5.0))
        p.add_line(PackingLine(carton_no="C1", gross_weight=3.0))
        p.add_line(PackingLine(carton_no="C2", gross_weight=2.0))
        p.calculate_summary()
        assert p.package_count == 2
        assert p.total_gross_weight == 10.0

    def test_mark_packed_sets_status_and_summary(self) -> None:
        p = PackingRecordAggregate()
        p.add_line(PackingLine(carton_no="C1", gross_weight=5.0, net_weight=4.0, volume=1.0))
        p.mark_packed(uuid4())
        assert p.status == PackingStatus.PACKED
        assert p.packed_at is not None
        assert p.total_gross_weight == 5.0

    def test_mark_packed_without_lines_rejected(self) -> None:
        p = PackingRecordAggregate()
        with pytest.raises(SALError) as exc:
            p.mark_packed(uuid4())
        assert exc.value.code == SALErrorCode.SHIPMENT_NOT_FOUND

    def test_mark_packed_twice_rejected(self) -> None:
        p = PackingRecordAggregate()
        p.add_line(PackingLine(carton_no="C1", gross_weight=5.0))
        p.mark_packed(uuid4())
        with pytest.raises(SALError) as exc:
            p.mark_packed(uuid4())
        assert exc.value.code == SALErrorCode.SHIPMENT_ORDER_INVALID

    def test_cancel_from_draft(self) -> None:
        p = PackingRecordAggregate()
        p.cancel()
        assert p.status == PackingStatus.CANCELLED

    def test_cancel_from_packed_rejected(self) -> None:
        p = PackingRecordAggregate()
        p.add_line(PackingLine(carton_no="C1", gross_weight=5.0))
        p.mark_packed(uuid4())
        with pytest.raises(SALError) as exc:
            p.cancel()
        assert exc.value.code == SALErrorCode.SHIPMENT_ORDER_INVALID