"""T16-05 策略服务与映射器单元测试。

覆盖 PutawayStrategyService 同品集中/就近/FIFO 建议排序、PickingStrategyService FIFO 选择+多库位拆分、
WmsToInvTransactionMapper P0 全作业类型→INV Transaction 映射、ReceivingQtyValidator 超收拒绝与部分收货累计。
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.domain.warehouse.services.picking_strategy_service import (
    PickableLocation,
    PickingAllocation,
    PickingStrategyService,
)
from app.domain.warehouse.services.putaway_strategy_service import (
    LocationCandidate,
    PutawayStrategyService,
)
from app.domain.warehouse.services.receiving_qty_validator import ReceivingQtyValidator
from app.domain.warehouse.services.wms_to_inv_transaction_mapper import (
    InvTransactionSpec,
    WmsToInvTransactionMapper,
)
from app.domain.warehouse.value_objects.wms_config import (
    PickingStrategy,
    PutawayStrategy,
)
from app.domain.warehouse.value_objects.wms_task_type import WmsTaskType
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode


def _candidate(
    *,
    code: str = "LOC",
    zone_function: str = "storage",
    existing_sku_qty: float = 0.0,
    distance: float | None = None,
    turnover_rate: float = 0.0,
) -> LocationCandidate:
    return LocationCandidate(
        location_id=uuid4(),
        location_code=code,
        zone_function=zone_function,
        existing_sku_qty=existing_sku_qty,
        distance=distance,
        turnover_rate=turnover_rate,
    )


def _pickable(
    *,
    code: str = "LOC",
    available_qty: float = 0.0,
    received_at: datetime | None = None,
    expiry_date: datetime | None = None,
) -> PickableLocation:
    return PickableLocation(
        location_id=uuid4(),
        location_code=code,
        available_qty=available_qty,
        received_at=received_at,
        expiry_date=expiry_date,
    )


class PutawayStrategyServiceTest:
    """PutawayStrategyService 上架策略库位建议排序测试。"""

    def test_same_product_concentrate_prioritizes_existing_sku(self) -> None:
        empty_loc = _candidate(code="A", existing_sku_qty=0.0)
        has_sku_loc = _candidate(code="B", existing_sku_qty=50.0)
        partial_loc = _candidate(code="C", existing_sku_qty=10.0)
        result = PutawayStrategyService.suggest(
            [empty_loc, has_sku_loc, partial_loc],
            PutawayStrategy.SAME_PRODUCT_CONCENTRATE,
        )
        assert result[0].location_code == "B"
        assert result[1].location_code == "C"
        assert result[2].location_code == "A"

    def test_nearest_sorts_by_distance_ascending(self) -> None:
        far = _candidate(code="A", distance=100.0)
        near = _candidate(code="B", distance=5.0)
        mid = _candidate(code="C", distance=50.0)
        result = PutawayStrategyService.suggest(
            [far, near, mid], PutawayStrategy.NEAREST
        )
        assert [r.location_code for r in result] == ["B", "C", "A"]

    def test_nearest_treats_none_distance_as_infinity(self) -> None:
        no_dist = _candidate(code="A", distance=None)
        has_dist = _candidate(code="B", distance=10.0)
        result = PutawayStrategyService.suggest(
            [no_dist, has_dist], PutawayStrategy.NEAREST
        )
        assert result[0].location_code == "B"
        assert result[1].location_code == "A"

    def test_zoned_prioritizes_storage(self) -> None:
        shipping = _candidate(code="A", zone_function="shipping")
        storage = _candidate(code="B", zone_function="storage")
        picking = _candidate(code="C", zone_function="picking")
        result = PutawayStrategyService.suggest(
            [shipping, storage, picking], PutawayStrategy.ZONED
        )
        assert result[0].zone_function == "storage"
        assert result[1].zone_function == "picking"
        assert result[2].zone_function == "shipping"

    def test_by_turnover_sorts_descending(self) -> None:
        low = _candidate(code="A", turnover_rate=1.0)
        high = _candidate(code="B", turnover_rate=100.0)
        mid = _candidate(code="C", turnover_rate=50.0)
        result = PutawayStrategyService.suggest(
            [low, high, mid], PutawayStrategy.BY_TURNOVER
        )
        assert [r.location_code for r in result] == ["B", "C", "A"]

    def test_unknown_strategy_returns_candidates_as_is(self) -> None:
        c1 = _candidate(code="A")
        c2 = _candidate(code="B")
        result = PutawayStrategyService.suggest([c1, c2], PutawayStrategy.MANUAL)
        assert len(result) == 2
        assert result[0].location_code == "A"

    def test_empty_candidates_returns_empty(self) -> None:
        result = PutawayStrategyService.suggest([], PutawayStrategy.NEAREST)
        assert result == []

    def test_single_candidate_preserved(self) -> None:
        c = _candidate(code="A", existing_sku_qty=10.0)
        result = PutawayStrategyService.suggest([c], PutawayStrategy.SAME_PRODUCT_CONCENTRATE)
        assert len(result) == 1
        assert result[0].location_code == "A"


class PickingStrategyServiceTest:
    """PickingStrategyService 拣货策略 FIFO 选择与多库位拆分测试。"""

    def test_fifo_sorts_by_received_at_ascending(self) -> None:
        old = _pickable(code="A", available_qty=100, received_at=datetime(2024, 1, 1, tzinfo=timezone.utc))
        new = _pickable(code="B", available_qty=100, received_at=datetime(2024, 6, 1, tzinfo=timezone.utc))
        result = PickingStrategyService.allocate([new, old], 50, PickingStrategy.FIFO)
        assert result[0].location_code == "A"

    def test_fifo_multi_location_split(self) -> None:
        """需 100，库位 A 仅 60，库位 B 50 → 拆分为 A:60 + B:40。"""
        loc_a = _pickable(code="A", available_qty=60, received_at=datetime(2024, 1, 1, tzinfo=timezone.utc))
        loc_b = _pickable(code="B", available_qty=50, received_at=datetime(2024, 1, 2, tzinfo=timezone.utc))
        result = PickingStrategyService.allocate([loc_a, loc_b], 100, PickingStrategy.FIFO)
        assert len(result) == 2
        assert result[0].location_code == "A"
        assert result[0].quantity == 60
        assert result[1].location_code == "B"
        assert result[1].quantity == 40

    def test_fifo_single_location_sufficient(self) -> None:
        loc = _pickable(code="A", available_qty=200, received_at=datetime(2024, 1, 1, tzinfo=timezone.utc))
        result = PickingStrategyService.allocate([loc], 100, PickingStrategy.FIFO)
        assert len(result) == 1
        assert result[0].quantity == 100

    def test_fifo_insufficient_total_quantity(self) -> None:
        loc_a = _pickable(code="A", available_qty=30, received_at=datetime(2024, 1, 1, tzinfo=timezone.utc))
        loc_b = _pickable(code="B", available_qty=20, received_at=datetime(2024, 1, 2, tzinfo=timezone.utc))
        result = PickingStrategyService.allocate([loc_a, loc_b], 100, PickingStrategy.FIFO)
        total = sum(a.quantity for a in result)
        assert total == 50

    def test_by_location_sorts_by_code(self) -> None:
        loc_z = _pickable(code="Z", available_qty=100)
        loc_a = _pickable(code="A", available_qty=100)
        result = PickingStrategyService.allocate([loc_z, loc_a], 50, PickingStrategy.BY_LOCATION)
        assert result[0].location_code == "A"

    def test_fefo_sorts_by_expiry_ascending(self) -> None:
        late_expiry = _pickable(code="A", available_qty=100, expiry_date=datetime(2025, 1, 1, tzinfo=timezone.utc))
        early_expiry = _pickable(code="B", available_qty=100, expiry_date=datetime(2024, 1, 1, tzinfo=timezone.utc))
        result = PickingStrategyService.allocate(
            [late_expiry, early_expiry], 50, PickingStrategy.FEFO
        )
        assert result[0].location_code == "B"

    def test_unknown_strategy_uses_original_order(self) -> None:
        loc_a = _pickable(code="A", available_qty=100)
        loc_b = _pickable(code="B", available_qty=100)
        result = PickingStrategyService.allocate([loc_a, loc_b], 50, PickingStrategy.MANUAL)
        assert result[0].location_code == "A"

    def test_zero_available_qty_skipped(self) -> None:
        loc_empty = _pickable(code="A", available_qty=0, received_at=datetime(2024, 1, 1, tzinfo=timezone.utc))
        loc_full = _pickable(code="B", available_qty=100, received_at=datetime(2024, 1, 2, tzinfo=timezone.utc))
        result = PickingStrategyService.allocate([loc_empty, loc_full], 50, PickingStrategy.FIFO)
        assert len(result) == 1
        assert result[0].location_code == "B"

    def test_zero_required_qty_returns_empty(self) -> None:
        loc = _pickable(code="A", available_qty=100)
        result = PickingStrategyService.allocate([loc], 0, PickingStrategy.FIFO)
        assert result == []

    def test_empty_locations_returns_empty(self) -> None:
        result = PickingStrategyService.allocate([], 100, PickingStrategy.FIFO)
        assert result == []


class WmsToInvTransactionMapperTest:
    """WmsToInvTransactionMapper P0 全作业类型→INV Transaction 映射测试。"""

    def test_map_receiving_with_inspection(self) -> None:
        task_id = uuid4()
        mapping = WmsToInvTransactionMapper.map_receiving(
            task_id=task_id,
            sku_id=uuid4(),
            warehouse_id=uuid4(),
            location_id=uuid4(),
            quantity=100,
            is_inspection_required=True,
        )
        assert mapping.task_type == WmsTaskType.RECEIVING
        assert len(mapping.specs) == 1
        spec = mapping.specs[0]
        assert spec.transaction_type == "purchase_receipt"
        assert spec.direction == "INBOUND"
        assert spec.state_field == "inspection"

    def test_map_receiving_inspection_exempt_direct_on_hand(self) -> None:
        mapping = WmsToInvTransactionMapper.map_receiving(
            task_id=uuid4(),
            sku_id=uuid4(),
            warehouse_id=uuid4(),
            location_id=uuid4(),
            quantity=100,
            is_inspection_required=False,
        )
        spec = mapping.specs[0]
        assert spec.transaction_type == "purchase_receipt"
        assert spec.state_field == "on_hand"

    def test_map_putaway_generates_transfer_out_and_in(self) -> None:
        mapping = WmsToInvTransactionMapper.map_putaway(
            task_id=uuid4(),
            sku_id=uuid4(),
            warehouse_id=uuid4(),
            source_location_id=uuid4(),
            target_location_id=uuid4(),
            quantity=50,
        )
        assert mapping.task_type == WmsTaskType.PUTAWAY
        assert len(mapping.specs) == 2
        assert mapping.specs[0].transaction_type == "transfer_out"
        assert mapping.specs[0].direction == "OUTBOUND"
        assert mapping.specs[1].transaction_type == "transfer_in"
        assert mapping.specs[1].direction == "INBOUND"

    def test_map_picking_sales_issue(self) -> None:
        reservation_id = uuid4()
        mapping = WmsToInvTransactionMapper.map_picking(
            task_id=uuid4(),
            sku_id=uuid4(),
            warehouse_id=uuid4(),
            location_id=uuid4(),
            quantity=30,
            is_sales=True,
            reservation_id=reservation_id,
        )
        assert mapping.task_type == WmsTaskType.PICKING
        spec = mapping.specs[0]
        assert spec.transaction_type == "sales_issue"
        assert spec.direction == "OUTBOUND"
        assert spec.state_field == "on_hand"
        assert spec.params["reservation_id"] == str(reservation_id)

    def test_map_picking_transfer_out_for_non_sales(self) -> None:
        mapping = WmsToInvTransactionMapper.map_picking(
            task_id=uuid4(),
            sku_id=uuid4(),
            warehouse_id=uuid4(),
            location_id=uuid4(),
            quantity=30,
            is_sales=False,
        )
        spec = mapping.specs[0]
        assert spec.transaction_type == "transfer_out"

    def test_map_transfer_generates_transfer_out_and_in(self) -> None:
        mapping = WmsToInvTransactionMapper.map_transfer(
            task_id=uuid4(),
            sku_id=uuid4(),
            warehouse_id=uuid4(),
            source_location_id=uuid4(),
            target_location_id=uuid4(),
            quantity=20,
        )
        assert mapping.task_type == WmsTaskType.TRANSFER
        assert len(mapping.specs) == 2
        assert mapping.specs[0].transaction_type == "transfer_out"
        assert mapping.specs[1].transaction_type == "transfer_in"

    def test_map_shipping_confirm_only(self) -> None:
        mapping = WmsToInvTransactionMapper.map_shipping(
            task_id=uuid4(),
            sku_id=uuid4(),
            warehouse_id=uuid4(),
            location_id=uuid4(),
            quantity=10,
        )
        assert mapping.task_type == WmsTaskType.SHIPPING
        spec = mapping.specs[0]
        assert spec.transaction_type == "sales_issue"
        assert spec.params.get("confirm_only") is True
        assert spec.params["quantity"] == 0

    def test_idempotency_key_derived_from_task_id(self) -> None:
        task_id = uuid4()
        mapping = WmsToInvTransactionMapper.map_receiving(
            task_id=task_id,
            sku_id=uuid4(),
            warehouse_id=uuid4(),
            location_id=uuid4(),
            quantity=10,
            is_inspection_required=True,
        )
        assert mapping.idempotency_key == f"wms:{task_id}:receiving"

    def test_correlation_id_propagated(self) -> None:
        mapping = WmsToInvTransactionMapper.map_putaway(
            task_id=uuid4(),
            sku_id=uuid4(),
            warehouse_id=uuid4(),
            source_location_id=uuid4(),
            target_location_id=uuid4(),
            quantity=10,
            correlation_id="corr-1",
        )
        assert mapping.correlation_id == "corr-1"

    def test_validate_mapping_coverage_returns_true(self) -> None:
        assert WmsToInvTransactionMapper.validate_mapping_coverage() is True

    def test_all_p0_task_types_covered(self) -> None:
        p0_types = {
            WmsTaskType.RECEIVING,
            WmsTaskType.PUTAWAY,
            WmsTaskType.PICKING,
            WmsTaskType.TRANSFER,
            WmsTaskType.SHIPPING,
        }
        task_id = uuid4()
        sku_id = uuid4()
        wh_id = uuid4()
        loc_id = uuid4()
        mappings = [
            WmsToInvTransactionMapper.map_receiving(task_id, sku_id, wh_id, loc_id, 1, True),
            WmsToInvTransactionMapper.map_putaway(task_id, sku_id, wh_id, loc_id, uuid4(), 1),
            WmsToInvTransactionMapper.map_picking(task_id, sku_id, wh_id, loc_id, 1),
            WmsToInvTransactionMapper.map_transfer(task_id, sku_id, wh_id, loc_id, uuid4(), 1),
            WmsToInvTransactionMapper.map_shipping(task_id, sku_id, wh_id, loc_id, 1),
        ]
        mapped_types = {m.task_type for m in mappings}
        assert p0_types == mapped_types


class ReceivingQtyValidatorTest:
    """ReceivingQtyValidator 超收拒绝与部分收货累计测试。"""

    def test_validate_passes_when_within_ordered(self) -> None:
        ReceivingQtyValidator.validate(ordered_qty=100, received_qty=0, current_qty=100)

    def test_validate_passes_partial(self) -> None:
        ReceivingQtyValidator.validate(ordered_qty=100, received_qty=30, current_qty=50)

    def test_validate_rejects_over_receive(self) -> None:
        with pytest.raises(WMSError) as exc:
            ReceivingQtyValidator.validate(ordered_qty=100, received_qty=0, current_qty=101)
        assert exc.value.code == WMSErrorCode.RECEIVING_OVER_RECEIVED

    def test_validate_rejects_accumulated_over_receive(self) -> None:
        with pytest.raises(WMSError) as exc:
            ReceivingQtyValidator.validate(ordered_qty=100, received_qty=80, current_qty=30)
        assert exc.value.code == WMSErrorCode.RECEIVING_OVER_RECEIVED

    def test_validate_rejects_negative_current_qty(self) -> None:
        with pytest.raises(WMSError) as exc:
            ReceivingQtyValidator.validate(ordered_qty=100, received_qty=0, current_qty=-1)
        assert exc.value.code == WMSErrorCode.RECEIVING_OVER_RECEIVED

    def test_validate_allows_over_receive_within_ratio(self) -> None:
        ReceivingQtyValidator.validate(
            ordered_qty=100, received_qty=0, current_qty=110, over_receive_ratio=0.1
        )

    def test_validate_rejects_over_receive_beyond_ratio(self) -> None:
        with pytest.raises(WMSError) as exc:
            ReceivingQtyValidator.validate(
                ordered_qty=100, received_qty=0, current_qty=111, over_receive_ratio=0.1
            )
        assert exc.value.code == WMSErrorCode.RECEIVING_OVER_RECEIVED

    def test_validate_exact_ordered_allowed(self) -> None:
        ReceivingQtyValidator.validate(ordered_qty=100, received_qty=0, current_qty=100)

    def test_validate_exact_ratio_boundary_allowed(self) -> None:
        ReceivingQtyValidator.validate(
            ordered_qty=100, received_qty=0, current_qty=110, over_receive_ratio=0.1
        )

    def test_can_receive_returns_true_when_valid(self) -> None:
        assert ReceivingQtyValidator.can_receive(ordered_qty=100, received_qty=0, current_qty=50) is True

    def test_can_receive_returns_false_when_over_received(self) -> None:
        assert ReceivingQtyValidator.can_receive(ordered_qty=100, received_qty=0, current_qty=101) is False

    def test_can_receive_returns_false_when_negative(self) -> None:
        assert ReceivingQtyValidator.can_receive(ordered_qty=100, received_qty=0, current_qty=-1) is False

    def test_over_receive_details_populated(self) -> None:
        with pytest.raises(WMSError) as exc:
            ReceivingQtyValidator.validate(
                ordered_qty=100, received_qty=20, current_qty=90, over_receive_ratio=0.0
            )
        assert exc.value.details["ordered_qty"] == 100
        assert exc.value.details["received_qty"] == 20
        assert exc.value.details["current_qty"] == 90
        assert exc.value.details["max_allowed"] == 100