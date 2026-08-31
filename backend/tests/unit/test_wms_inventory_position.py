"""T16-03 InventoryPosition 聚合根与 WMS→INV 状态映射单元测试。

覆盖 InventoryPositionAggregate 组合键唯一性、非负数量、状态流转、批次可空、
禁止直接修改；WmsToInvStateMapper 六状态映射；InventoryPositionSyncService 作业后同步。
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from app.domain.shared.entity import EntityId
from app.domain.warehouse.aggregates.inventory_position_aggregate import (
    InventoryPositionAggregate,
)
from app.domain.warehouse.services.inventory_position_sync_service import (
    InventoryPositionSyncService,
    InvTransactionResult,
)
from app.domain.warehouse.services.wms_to_inv_state_mapper import WmsToInvStateMapper
from app.domain.warehouse.value_objects.batch_lot import BatchLot
from app.domain.warehouse.value_objects.inventory_status import (
    InventoryStatus,
    is_valid_transition,
)
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode


def _make_position(
    *,
    quantity: float = 0,
    inventory_status: InventoryStatus = InventoryStatus.AVAILABLE,
    batch_lot: BatchLot | None = None,
    location_id: uuid4 | None = None,
) -> InventoryPositionAggregate:
    return InventoryPositionAggregate(
        id=EntityId.generate(),
        tenant_id=uuid4(),
        sku_id=uuid4(),
        warehouse_id=uuid4(),
        location_id=location_id or uuid4(),
        quantity=quantity,
        inventory_status=inventory_status,
        batch_lot=batch_lot,
    )


class InventoryStatusTest:
    """InventoryStatus 六状态枚举与流转规则测试。"""

    def test_all_six_statuses_present(self) -> None:
        expected = {"available", "in_qc", "blocked", "in_transit", "quarantined", "returned"}
        actual = {s.value for s in InventoryStatus}
        assert actual == expected

    def test_count_is_six(self) -> None:
        assert len(list(InventoryStatus)) == 6

    def test_same_status_is_valid_transition(self) -> None:
        for status in InventoryStatus:
            assert is_valid_transition(status, status) is True

    def test_available_can_transition_to_four_states(self) -> None:
        for target in (InventoryStatus.IN_QC, InventoryStatus.BLOCKED,
                       InventoryStatus.IN_TRANSIT, InventoryStatus.QUARANTINED):
            assert is_valid_transition(InventoryStatus.AVAILABLE, target) is True

    def test_available_cannot_transition_to_returned(self) -> None:
        assert is_valid_transition(InventoryStatus.AVAILABLE, InventoryStatus.RETURNED) is False

    def test_in_qc_transitions(self) -> None:
        for target in (InventoryStatus.AVAILABLE, InventoryStatus.QUARANTINED, InventoryStatus.RETURNED):
            assert is_valid_transition(InventoryStatus.IN_QC, target) is True
        assert is_valid_transition(InventoryStatus.IN_QC, InventoryStatus.BLOCKED) is False

    def test_blocked_transitions(self) -> None:
        for target in (InventoryStatus.AVAILABLE, InventoryStatus.QUARANTINED):
            assert is_valid_transition(InventoryStatus.BLOCKED, target) is True
        assert is_valid_transition(InventoryStatus.BLOCKED, InventoryStatus.IN_QC) is False

    def test_in_transit_only_to_available(self) -> None:
        assert is_valid_transition(InventoryStatus.IN_TRANSIT, InventoryStatus.AVAILABLE) is True
        assert is_valid_transition(InventoryStatus.IN_TRANSIT, InventoryStatus.BLOCKED) is False

    def test_quarantined_transitions(self) -> None:
        for target in (InventoryStatus.AVAILABLE, InventoryStatus.BLOCKED, InventoryStatus.RETURNED):
            assert is_valid_transition(InventoryStatus.QUARANTINED, target) is True

    def test_returned_transitions(self) -> None:
        for target in (InventoryStatus.AVAILABLE, InventoryStatus.BLOCKED):
            assert is_valid_transition(InventoryStatus.RETURNED, target) is True
        assert is_valid_transition(InventoryStatus.RETURNED, InventoryStatus.IN_QC) is False


class BatchLotTest:
    """BatchLot 批次/批号/序列号值对象测试 - P0 预留可空。"""

    def test_default_batch_lot_is_empty(self) -> None:
        bl = BatchLot()
        assert bl.is_empty() is True
        assert bl.batch_number is None
        assert bl.lot_number is None
        assert bl.serial_number is None
        assert bl.expiry_date is None
        assert bl.production_date is None

    def test_populated_batch_lot_not_empty(self) -> None:
        bl = BatchLot(batch_number="B001", lot_number="L001", serial_number="S001")
        assert bl.is_empty() is False

    def test_is_expired_false_when_no_expiry(self) -> None:
        assert BatchLot().is_expired() is False

    def test_is_expired_true_when_past_expiry(self) -> None:
        bl = BatchLot(expiry_date=date(2020, 1, 1))
        assert bl.is_expired(today=date(2020, 1, 2)) is True

    def test_is_expired_false_when_future_expiry(self) -> None:
        bl = BatchLot(expiry_date=date(2030, 1, 1))
        assert bl.is_expired(today=date(2020, 1, 1)) is False

    def test_is_near_expiry(self) -> None:
        bl = BatchLot(expiry_date=date(2020, 1, 25))
        assert bl.is_near_expiry(threshold_days=30, today=date(2020, 1, 1)) is True

    def test_is_near_expiry_false_when_far(self) -> None:
        bl = BatchLot(expiry_date=date(2020, 12, 31))
        assert bl.is_near_expiry(threshold_days=30, today=date(2020, 1, 1)) is False

    def test_composite_key(self) -> None:
        bl = BatchLot(batch_number="B1", lot_number="L1", serial_number="S1")
        assert bl.composite_key() == "B1|L1|S1"

    def test_composite_key_empty_when_all_none(self) -> None:
        assert BatchLot().composite_key() == "||"


class InventoryPositionAggregateTest:
    """InventoryPositionAggregate 库存位置聚合根测试。"""

    def test_construction_persists_all_fields(self) -> None:
        tenant_id = uuid4()
        sku_id = uuid4()
        warehouse_id = uuid4()
        location_id = uuid4()
        bin_id = uuid4()
        bl = BatchLot(batch_number="B1")
        pos = InventoryPositionAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            sku_id=sku_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            quantity=50,
            inventory_status=InventoryStatus.AVAILABLE,
            bin_id=bin_id,
            batch_lot=bl,
        )
        assert pos.tenant_id == tenant_id
        assert pos.sku_id == sku_id
        assert pos.warehouse_id == warehouse_id
        assert pos.location_id == location_id
        assert pos.bin_id == bin_id
        assert pos.quantity == 50
        assert pos.inventory_status == InventoryStatus.AVAILABLE
        assert pos.batch_lot.batch_number == "B1"

    def test_default_quantity_zero_and_available(self) -> None:
        pos = _make_position()
        assert pos.quantity == 0
        assert pos.inventory_status == InventoryStatus.AVAILABLE

    def test_composite_key_uniqueness(self) -> None:
        tenant_id = uuid4()
        sku_id = uuid4()
        location_id = uuid4()
        bl = BatchLot(batch_number="B1", lot_number="L1", serial_number="S1")
        pos_a = InventoryPositionAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            sku_id=sku_id,
            warehouse_id=uuid4(),
            location_id=location_id,
            batch_lot=bl,
            inventory_status=InventoryStatus.AVAILABLE,
        )
        pos_b = InventoryPositionAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            sku_id=sku_id,
            warehouse_id=uuid4(),
            location_id=location_id,
            batch_lot=bl,
            inventory_status=InventoryStatus.AVAILABLE,
        )
        assert pos_a.composite_key() == pos_b.composite_key()

    def test_composite_key_differs_by_status(self) -> None:
        pos_available = _make_position(inventory_status=InventoryStatus.AVAILABLE)
        pos_blocked = InventoryPositionAggregate(
            id=EntityId.generate(),
            tenant_id=pos_available.tenant_id,
            sku_id=pos_available.sku_id,
            warehouse_id=pos_available.warehouse_id,
            location_id=pos_available.location_id,
            inventory_status=InventoryStatus.BLOCKED,
        )
        assert pos_available.composite_key() != pos_blocked.composite_key()

    def test_composite_key_differs_by_batch(self) -> None:
        base = _make_position()
        pos_a = InventoryPositionAggregate(
            id=EntityId.generate(),
            tenant_id=base.tenant_id,
            sku_id=base.sku_id,
            warehouse_id=base.warehouse_id,
            location_id=base.location_id,
            batch_lot=BatchLot(batch_number="B1"),
        )
        pos_b = InventoryPositionAggregate(
            id=EntityId.generate(),
            tenant_id=base.tenant_id,
            sku_id=base.sku_id,
            warehouse_id=base.warehouse_id,
            location_id=base.location_id,
            batch_lot=BatchLot(batch_number="B2"),
        )
        assert pos_a.composite_key() != pos_b.composite_key()

    def test_add_quantity_increases(self) -> None:
        pos = _make_position(quantity=10)
        pos.add_quantity(5)
        assert pos.quantity == 15

    def test_add_quantity_rejects_negative(self) -> None:
        pos = _make_position(quantity=10)
        with pytest.raises(WMSError) as exc:
            pos.add_quantity(-5)
        assert exc.value.code == WMSErrorCode.SERVICE_UNAVAILABLE

    def test_add_quantity_zero_allowed(self) -> None:
        pos = _make_position(quantity=10)
        pos.add_quantity(0)
        assert pos.quantity == 10

    def test_reduce_quantity_decreases(self) -> None:
        pos = _make_position(quantity=10)
        pos.reduce_quantity(4)
        assert pos.quantity == 6

    def test_reduce_quantity_rejects_negative(self) -> None:
        pos = _make_position(quantity=10)
        with pytest.raises(WMSError) as exc:
            pos.reduce_quantity(-1)
        assert exc.value.code == WMSErrorCode.SERVICE_UNAVAILABLE

    def test_reduce_quantity_rejects_insufficient(self) -> None:
        pos = _make_position(quantity=3)
        with pytest.raises(WMSError) as exc:
            pos.reduce_quantity(5)
        assert exc.value.code == WMSErrorCode.PICKING_INSUFFICIENT_AVAILABLE
        assert exc.value.details["current_qty"] == 3
        assert exc.value.details["reduce_qty"] == 5

    def test_reduce_quantity_to_exact_zero_allowed(self) -> None:
        pos = _make_position(quantity=5)
        pos.reduce_quantity(5)
        assert pos.quantity == 0

    def test_transfer_to_new_location(self) -> None:
        pos = _make_position()
        new_loc = uuid4()
        new_bin = uuid4()
        pos.transfer_to(new_loc, new_bin)
        assert pos.location_id == new_loc
        assert pos.bin_id == new_bin

    def test_transfer_to_same_location_is_noop(self) -> None:
        location_id = uuid4()
        bin_id = uuid4()
        pos = InventoryPositionAggregate(
            id=EntityId.generate(),
            tenant_id=uuid4(),
            sku_id=uuid4(),
            warehouse_id=uuid4(),
            location_id=location_id,
            bin_id=bin_id,
        )
        pos.transfer_to(location_id, bin_id)
        assert pos.location_id == location_id
        assert pos.bin_id == bin_id

    def test_change_status_valid_transition(self) -> None:
        pos = _make_position(inventory_status=InventoryStatus.AVAILABLE)
        pos.change_status(InventoryStatus.IN_QC)
        assert pos.inventory_status == InventoryStatus.IN_QC

    def test_change_status_same_status_is_noop(self) -> None:
        pos = _make_position(inventory_status=InventoryStatus.AVAILABLE)
        pos.change_status(InventoryStatus.AVAILABLE)
        assert pos.inventory_status == InventoryStatus.AVAILABLE

    def test_change_status_invalid_transition_rejected(self) -> None:
        pos = _make_position(inventory_status=InventoryStatus.AVAILABLE)
        with pytest.raises(WMSError) as exc:
            pos.change_status(InventoryStatus.RETURNED)
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION

    def test_change_status_in_transit_to_blocked_rejected(self) -> None:
        pos = _make_position(inventory_status=InventoryStatus.IN_TRANSIT)
        with pytest.raises(WMSError) as exc:
            pos.change_status(InventoryStatus.BLOCKED)
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION

    def test_quantity_property_is_read_only(self) -> None:
        """禁止直接修改：quantity 无 setter，赋值抛 AttributeError。"""
        pos = _make_position(quantity=10)
        with pytest.raises(AttributeError):
            pos.quantity = 999  # type: ignore[misc]

    def test_inventory_status_property_is_read_only(self) -> None:
        pos = _make_position()
        with pytest.raises(AttributeError):
            pos.inventory_status = InventoryStatus.BLOCKED  # type: ignore[misc]

    def test_add_quantity_records_event(self) -> None:
        pos = _make_position(quantity=10)
        pos.add_quantity(5)
        events = list(pos.pull_events())
        assert len(events) == 1

    def test_reduce_quantity_records_event(self) -> None:
        pos = _make_position(quantity=10)
        pos.reduce_quantity(3)
        events = list(pos.pull_events())
        assert len(events) == 1


class WmsToInvStateMapperTest:
    """WmsToInvStateMapper 六状态→INV 状态字段映射测试。"""

    @pytest.mark.parametrize(
        "wms_status,expected_field",
        [
            (InventoryStatus.AVAILABLE, "on_hand"),
            (InventoryStatus.IN_QC, "inspection"),
            (InventoryStatus.BLOCKED, "blocked"),
            (InventoryStatus.IN_TRANSIT, "in_transit"),
            (InventoryStatus.QUARANTINED, "blocked"),
            (InventoryStatus.RETURNED, "on_hand"),
        ],
    )
    def test_to_inv_state_field_mapping(
        self, wms_status: InventoryStatus, expected_field: str
    ) -> None:
        assert WmsToInvStateMapper.to_inv_state_field(wms_status) == expected_field

    def test_to_inv_delta_returns_single_field(self) -> None:
        delta = WmsToInvStateMapper.to_inv_delta(InventoryStatus.AVAILABLE, 100.0)
        assert delta == {"on_hand": 100.0}

    def test_to_inv_delta_for_blocked(self) -> None:
        delta = WmsToInvStateMapper.to_inv_delta(InventoryStatus.BLOCKED, 50.0)
        assert delta == {"blocked": 50.0}

    def test_to_inv_delta_for_quarantined_maps_to_blocked(self) -> None:
        delta = WmsToInvStateMapper.to_inv_delta(InventoryStatus.QUARANTINED, 20.0)
        assert delta == {"blocked": 20.0}

    def test_is_on_hand_equivalent(self) -> None:
        assert WmsToInvStateMapper.is_on_hand_equivalent(InventoryStatus.AVAILABLE) is True
        assert WmsToInvStateMapper.is_on_hand_equivalent(InventoryStatus.RETURNED) is True
        assert WmsToInvStateMapper.is_on_hand_equivalent(InventoryStatus.BLOCKED) is False

    def test_is_blocked_equivalent(self) -> None:
        assert WmsToInvStateMapper.is_blocked_equivalent(InventoryStatus.BLOCKED) is True
        assert WmsToInvStateMapper.is_blocked_equivalent(InventoryStatus.QUARANTINED) is True
        assert WmsToInvStateMapper.is_blocked_equivalent(InventoryStatus.AVAILABLE) is False

    def test_all_six_statuses_mapped(self) -> None:
        for status in InventoryStatus:
            field = WmsToInvStateMapper.to_inv_state_field(status)
            assert field in {"on_hand", "inspection", "blocked", "in_transit"}


class InventoryPositionSyncServiceTest:
    """InventoryPositionSyncService 作业后同步正确性测试。"""

    def _make_inv_result(
        self,
        *,
        transaction_type: str = "purchase_receipt",
        quantity: float = 10.0,
        direction: str = "INBOUND",
        location_id: uuid4 | None = None,
    ) -> InvTransactionResult:
        return InvTransactionResult(
            transaction_id=uuid4(),
            transaction_type=transaction_type,
            sku_id=uuid4(),
            warehouse_id=uuid4(),
            location_id=location_id or uuid4(),
            quantity=quantity,
            direction=direction,
        )

    def test_sync_inbound_purchase_receipt_adds_quantity(self) -> None:
        pos = _make_position(quantity=0, inventory_status=InventoryStatus.AVAILABLE)
        result = self._make_inv_result(
            transaction_type="purchase_receipt", quantity=50, direction="INBOUND"
        )
        updated = InventoryPositionSyncService.sync_after_inv_transaction(pos, result)
        assert updated.quantity == 50
        assert updated.inventory_status == InventoryStatus.AVAILABLE

    def test_sync_outbound_sales_issue_reduces_quantity(self) -> None:
        pos = _make_position(quantity=100, inventory_status=InventoryStatus.AVAILABLE)
        result = self._make_inv_result(
            transaction_type="sales_issue", quantity=30, direction="OUTBOUND"
        )
        updated = InventoryPositionSyncService.sync_after_inv_transaction(pos, result)
        assert updated.quantity == 70

    def test_sync_transfer_out_changes_status_to_in_transit(self) -> None:
        pos = _make_position(quantity=50, inventory_status=InventoryStatus.AVAILABLE)
        result = self._make_inv_result(
            transaction_type="transfer_out", quantity=20, direction="OUTBOUND"
        )
        updated = InventoryPositionSyncService.sync_after_inv_transaction(pos, result)
        assert updated.inventory_status == InventoryStatus.IN_TRANSIT
        assert updated.quantity == 30

    def test_sync_block_changes_status_to_blocked(self) -> None:
        pos = _make_position(quantity=10, inventory_status=InventoryStatus.AVAILABLE)
        result = self._make_inv_result(
            transaction_type="block", quantity=10, direction="INBOUND"
        )
        updated = InventoryPositionSyncService.sync_after_inv_transaction(pos, result)
        assert updated.inventory_status == InventoryStatus.BLOCKED
        assert updated.quantity == 20

    def test_sync_inspection_in_changes_status_to_in_qc(self) -> None:
        pos = _make_position(quantity=10, inventory_status=InventoryStatus.AVAILABLE)
        result = self._make_inv_result(
            transaction_type="inspection_in", quantity=10, direction="INBOUND"
        )
        updated = InventoryPositionSyncService.sync_after_inv_transaction(pos, result)
        assert updated.inventory_status == InventoryStatus.IN_QC

    def test_sync_after_transfer_reduces_source_and_adds_target(self) -> None:
        source = _make_position(quantity=100)
        target = _make_position(quantity=0)
        qty = 40
        new_location_id = target.location_id
        src, tgt = InventoryPositionSyncService.sync_after_transfer(
            source, target, qty, new_location_id
        )
        assert src.quantity == 60
        assert tgt.quantity == 40

    def test_sync_after_transfer_moves_source_location(self) -> None:
        source = _make_position(quantity=100)
        target = _make_position(quantity=0)
        new_location_id = uuid4()
        src, _ = InventoryPositionSyncService.sync_after_transfer(
            source, target, 40, new_location_id
        )
        assert src.location_id == new_location_id

    def test_sync_after_transfer_no_location_move_when_same(self) -> None:
        source = _make_position(quantity=100)
        target = _make_position(quantity=0)
        original_source_loc = source.location_id
        src, tgt = InventoryPositionSyncService.sync_after_transfer(
            source, target, 40, original_source_loc
        )
        assert src.location_id == original_source_loc
        assert tgt.quantity == 40

    def test_sync_unknown_transaction_type_defaults_to_available(self) -> None:
        pos = _make_position(quantity=5, inventory_status=InventoryStatus.IN_QC)
        result = self._make_inv_result(
            transaction_type="unknown_type", quantity=10, direction="INBOUND"
        )
        updated = InventoryPositionSyncService.sync_after_inv_transaction(pos, result)
        assert updated.inventory_status == InventoryStatus.AVAILABLE
        assert updated.quantity == 15