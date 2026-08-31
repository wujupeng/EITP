"""T16-02 空间管理聚合与校验服务单元测试。

覆盖 LocationAggregate 容量多维校验与启停控制、ZoneAggregate 六功能枚举、
HierarchyCycleGuard DFS 无环检测与循环拒绝、ZoneFunctionGuard 作业类型匹配。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.shared.entity import EntityId
from app.domain.warehouse.aggregates.location_aggregate import (
    LocationAggregate,
    LocationStatus,
)
from app.domain.warehouse.aggregates.zone_aggregate import ZoneAggregate, ZoneStatus
from app.domain.warehouse.services.hierarchy_cycle_guard import HierarchyCycleGuard
from app.domain.warehouse.services.zone_function_guard import (
    OperationType,
    ZoneFunctionGuard,
)
from app.domain.warehouse.value_objects.capacity import (
    Capacity,
    CapacityCheckResult,
    CapacityEnforceModeWms,
)
from app.domain.warehouse.value_objects.coordinate import Coordinate
from app.domain.warehouse.value_objects.location_type_wms import LocationTypeWms
from app.domain.warehouse.value_objects.zone_function import (
    ZoneFunction,
    location_type_for_zone_function,
)
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode


def _make_location(
    *,
    capacity: Capacity | None = None,
    status: LocationStatus = LocationStatus.ACTIVE,
    location_code: str = "LOC-001",
) -> LocationAggregate:
    return LocationAggregate(
        id=EntityId.generate(),
        tenant_id=uuid4(),
        warehouse_id=uuid4(),
        zone_id=uuid4(),
        location_code=location_code,
        capacity=capacity,
        status=status,
    )


def _make_zone(
    *,
    zone_function: ZoneFunction = ZoneFunction.STORAGE,
    status: ZoneStatus = ZoneStatus.ACTIVE,
) -> ZoneAggregate:
    return ZoneAggregate(
        id=EntityId.generate(),
        tenant_id=uuid4(),
        warehouse_id=uuid4(),
        zone_code="ZONE-001",
        zone_name="存储区",
        zone_function=zone_function,
        status=status,
    )


class LocationAggregateTest:
    """LocationAggregate 库位聚合根测试。"""

    def test_construction_persists_all_fields(self) -> None:
        tenant_id = uuid4()
        warehouse_id = uuid4()
        zone_id = uuid4()
        area_id = uuid4()
        loc = LocationAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            warehouse_id=warehouse_id,
            zone_id=zone_id,
            location_code="A-01-02",
            location_type=LocationTypeWms.SHELF,
            area_id=area_id,
        )
        assert loc.tenant_id == tenant_id
        assert loc.warehouse_id == warehouse_id
        assert loc.zone_id == zone_id
        assert loc.area_id == area_id
        assert loc.location_code == "A-01-02"
        assert loc.location_type == LocationTypeWms.SHELF
        assert loc.is_active() is True

    def test_location_code_uniqueness_is_identity_based(self) -> None:
        """location_code 在仓库内唯一由仓储层保证；聚合根以 id 区分实体。"""
        loc_a = _make_location(location_code="DUP-001")
        loc_b = _make_location(location_code="DUP-001")
        assert loc_a.location_code == loc_b.location_code
        assert loc_a.id != loc_b.id
        assert loc_a != loc_b

    def test_enable_disable_control(self) -> None:
        loc = _make_location()
        assert loc.is_active() is True
        loc.disable()
        assert loc.status == LocationStatus.INACTIVE
        assert loc.is_active() is False
        loc.enable()
        assert loc.status == LocationStatus.ACTIVE
        assert loc.is_active() is True

    def test_disable_idempotent(self) -> None:
        loc = _make_location(status=LocationStatus.INACTIVE)
        loc.disable()
        assert loc.status == LocationStatus.INACTIVE

    def test_enable_idempotent(self) -> None:
        loc = _make_location(status=LocationStatus.ACTIVE)
        loc.enable()
        assert loc.status == LocationStatus.ACTIVE

    def test_disable_records_event(self) -> None:
        loc = _make_location()
        loc.disable()
        events = list(loc.pull_events())
        assert len(events) == 1

    def test_check_capacity_passes_when_within_limits(self) -> None:
        cap = Capacity(
            max_qty=100,
            max_weight=50,
            max_volume=20,
            capacity_enforce_mode=CapacityEnforceModeWms.REJECT,
        )
        loc = _make_location(capacity=cap)
        result = loc.check_capacity(add_qty=10, add_weight=5, add_volume=2)
        assert result.allowed is True
        assert result.exceeded is False

    def test_check_capacity_reject_mode_raises_on_qty_exceeded(self) -> None:
        cap = Capacity(
            max_qty=100,
            capacity_enforce_mode=CapacityEnforceModeWms.REJECT,
        )
        loc = _make_location(capacity=cap)
        with pytest.raises(WMSError) as exc:
            loc.check_capacity(add_qty=80, current_qty=30)
        assert exc.value.code == WMSErrorCode.LOCATION_CAPACITY_EXCEEDED
        assert "qty" in exc.value.details["exceeded_dims"]

    def test_check_capacity_reject_mode_raises_on_weight_exceeded(self) -> None:
        cap = Capacity(
            max_weight=50,
            capacity_enforce_mode=CapacityEnforceModeWms.REJECT,
        )
        loc = _make_location(capacity=cap)
        with pytest.raises(WMSError) as exc:
            loc.check_capacity(add_weight=40, current_weight=20)
        assert exc.value.code == WMSErrorCode.LOCATION_CAPACITY_EXCEEDED
        assert "weight" in exc.value.details["exceeded_dims"]

    def test_check_capacity_reject_mode_raises_on_volume_exceeded(self) -> None:
        cap = Capacity(
            max_volume=20,
            capacity_enforce_mode=CapacityEnforceModeWms.REJECT,
        )
        loc = _make_location(capacity=cap)
        with pytest.raises(WMSError) as exc:
            loc.check_capacity(add_volume=15, current_volume=10)
        assert exc.value.code == WMSErrorCode.LOCATION_CAPACITY_EXCEEDED
        assert "volume" in exc.value.details["exceeded_dims"]

    def test_check_capacity_warn_mode_does_not_raise(self) -> None:
        cap = Capacity(
            max_qty=100,
            capacity_enforce_mode=CapacityEnforceModeWms.WARN,
        )
        loc = _make_location(capacity=cap)
        result = loc.check_capacity(add_qty=80, current_qty=30)
        assert result.exceeded is True
        assert result.allowed is True

    def test_check_capacity_multi_dimension_exceeded(self) -> None:
        cap = Capacity(
            max_qty=100,
            max_weight=50,
            capacity_enforce_mode=CapacityEnforceModeWms.REJECT,
        )
        loc = _make_location(capacity=cap)
        with pytest.raises(WMSError) as exc:
            loc.check_capacity(add_qty=80, current_qty=30, add_weight=40, current_weight=20)
        assert exc.value.code == WMSErrorCode.LOCATION_CAPACITY_EXCEEDED
        dims = exc.value.details["exceeded_dims"]
        assert "qty" in dims
        assert "weight" in dims

    def test_check_capacity_none_dimension_not_checked(self) -> None:
        cap = Capacity(max_qty=100, capacity_enforce_mode=CapacityEnforceModeWms.REJECT)
        loc = _make_location(capacity=cap)
        result = loc.check_capacity(add_qty=10, add_weight=999, add_volume=999)
        assert result.allowed is True

    def test_check_capacity_rejects_when_location_disabled(self) -> None:
        cap = Capacity(max_qty=100, capacity_enforce_mode=CapacityEnforceModeWms.REJECT)
        loc = _make_location(capacity=cap, status=LocationStatus.INACTIVE)
        with pytest.raises(WMSError) as exc:
            loc.check_capacity(add_qty=1)
        assert exc.value.code == WMSErrorCode.LOCATION_DISABLED

    def test_update_coordinate_when_active(self) -> None:
        loc = _make_location()
        new_coord = Coordinate(x=1.0, y=2.0, z=3.0)
        loc.update_coordinate(new_coord)
        assert loc.coordinate.x == 1.0
        assert loc.coordinate.y == 2.0
        assert loc.coordinate.z == 3.0

    def test_update_coordinate_rejected_when_disabled(self) -> None:
        loc = _make_location(status=LocationStatus.INACTIVE)
        with pytest.raises(WMSError) as exc:
            loc.update_coordinate(Coordinate(x=1.0))
        assert exc.value.code == WMSErrorCode.LOCATION_DISABLED

    def test_check_zone_function_is_no_op(self) -> None:
        loc = _make_location()
        loc.check_zone_function(ZoneFunction.STORAGE)


class CapacityTest:
    """Capacity 多维度容量值对象测试。"""

    def test_default_capacity_unlimited(self) -> None:
        cap = Capacity()
        result = cap.check(add_qty=99999, add_weight=99999, add_volume=99999)
        assert result.allowed is True
        assert result.exceeded is False

    def test_warn_mode_allows_but_flags_exceeded(self) -> None:
        cap = Capacity(max_qty=10, capacity_enforce_mode=CapacityEnforceModeWms.WARN)
        result = cap.check(add_qty=15)
        assert result.exceeded is True
        assert result.allowed is True
        assert result.exceeded_dims == ["qty"]

    def test_reject_mode_blocks_exceeded(self) -> None:
        cap = Capacity(max_qty=10, capacity_enforce_mode=CapacityEnforceModeWms.REJECT)
        result = cap.check(add_qty=15)
        assert result.exceeded is True
        assert result.allowed is False

    def test_check_result_message_populated_when_exceeded(self) -> None:
        cap = Capacity(max_qty=10, capacity_enforce_mode=CapacityEnforceModeWms.REJECT)
        result = cap.check(add_qty=15)
        assert "qty" in result.message

    def test_check_result_message_empty_when_ok(self) -> None:
        cap = Capacity(max_qty=100)
        result = cap.check(add_qty=10)
        assert result.message == ""


class CoordinateTest:
    """Coordinate 坐标值对象测试。"""

    def test_default_coordinate_not_set(self) -> None:
        coord = Coordinate()
        assert coord.is_set() is False

    def test_is_set_true_when_any_axis_present(self) -> None:
        assert Coordinate(x=1.0).is_set() is True
        assert Coordinate(y=1.0).is_set() is True
        assert Coordinate(z=1.0).is_set() is True

    def test_distance_to_returns_none_when_unset(self) -> None:
        assert Coordinate().distance_to(Coordinate(x=1.0)) is None
        assert Coordinate(x=1.0).distance_to(Coordinate()) is None

    def test_distance_to_computes_euclidean(self) -> None:
        a = Coordinate(x=0.0, y=0.0, z=0.0)
        b = Coordinate(x=3.0, y=4.0, z=0.0)
        assert a.distance_to(b) == 5.0

    def test_distance_to_self_is_zero(self) -> None:
        a = Coordinate(x=1.0, y=2.0, z=3.0)
        assert a.distance_to(a) == 0.0


class ZoneAggregateTest:
    """ZoneAggregate 库区聚合根与 ZoneFunction 六功能枚举测试。"""

    def test_all_six_zone_functions_present(self) -> None:
        expected = {"receiving", "storage", "picking", "shipping", "qc", "blocked"}
        actual = {zf.value for zf in ZoneFunction}
        assert actual == expected

    def test_zone_function_count_is_six(self) -> None:
        assert len(list(ZoneFunction)) == 6

    @pytest.mark.parametrize(
        "zf,expected_value",
        [
            (ZoneFunction.RECEIVING, "receiving"),
            (ZoneFunction.STORAGE, "storage"),
            (ZoneFunction.PICKING, "picking"),
            (ZoneFunction.SHIPPING, "shipping"),
            (ZoneFunction.QC, "qc"),
            (ZoneFunction.BLOCKED, "blocked"),
        ],
    )
    def test_zone_function_values(self, zf: ZoneFunction, expected_value: str) -> None:
        assert zf.value == expected_value

    def test_construction_persists_fields(self) -> None:
        zone = _make_zone(zone_function=ZoneFunction.RECEIVING)
        assert zone.zone_code == "ZONE-001"
        assert zone.zone_name == "存储区"
        assert zone.zone_function == ZoneFunction.RECEIVING
        assert zone.is_active() is True

    def test_enable_disable(self) -> None:
        zone = _make_zone()
        zone.disable()
        assert zone.status == ZoneStatus.DISABLED
        assert zone.is_active() is False
        zone.enable()
        assert zone.status == ZoneStatus.ACTIVE
        assert zone.is_active() is True

    def test_update_name(self) -> None:
        zone = _make_zone()
        zone.update_name("新名称")
        assert zone.zone_name == "新名称"

    def test_update_name_rejects_empty(self) -> None:
        zone = _make_zone()
        with pytest.raises(WMSError) as exc:
            zone.update_name("   ")
        assert exc.value.code == WMSErrorCode.SERVICE_UNAVAILABLE

    def test_location_type_for_zone_function_mapping(self) -> None:
        assert location_type_for_zone_function(ZoneFunction.RECEIVING).value == "receiving"
        assert location_type_for_zone_function(ZoneFunction.STORAGE).value == "storage"
        assert location_type_for_zone_function(ZoneFunction.PICKING).value == "picking"
        assert location_type_for_zone_function(ZoneFunction.SHIPPING).value == "storage"
        assert location_type_for_zone_function(ZoneFunction.QC).value == "inspection"
        assert location_type_for_zone_function(ZoneFunction.BLOCKED).value == "storage"


class HierarchyCycleGuardTest:
    """HierarchyCycleGuard DFS 无环检测与循环拒绝测试。"""

    def test_empty_map_has_no_cycle(self) -> None:
        assert HierarchyCycleGuard.has_cycle({}) is False

    def test_linear_hierarchy_no_cycle(self) -> None:
        a, b, c = uuid4(), uuid4(), uuid4()
        parent_map = {a: None, b: a, c: b}
        assert HierarchyCycleGuard.has_cycle(parent_map) is False

    def test_self_reference_is_cycle(self) -> None:
        a = uuid4()
        parent_map = {a: a}
        assert HierarchyCycleGuard.has_cycle(parent_map) is True

    def test_two_node_cycle_detected(self) -> None:
        a, b = uuid4(), uuid4()
        parent_map = {a: b, b: a}
        assert HierarchyCycleGuard.has_cycle(parent_map) is True

    def test_three_node_cycle_detected(self) -> None:
        a, b, c = uuid4(), uuid4(), uuid4()
        parent_map = {a: b, b: c, c: a}
        assert HierarchyCycleGuard.has_cycle(parent_map) is True

    def test_dag_with_shared_root_no_cycle(self) -> None:
        root = uuid4()
        a, b, c = uuid4(), uuid4(), uuid4()
        parent_map = {root: None, a: root, b: root, c: a}
        assert HierarchyCycleGuard.has_cycle(parent_map) is False

    def test_validate_passes_when_no_cycle(self) -> None:
        a, b = uuid4(), uuid4()
        HierarchyCycleGuard.validate({a: None, b: a})

    def test_validate_raises_when_cycle(self) -> None:
        a, b = uuid4(), uuid4()
        with pytest.raises(WMSError) as exc:
            HierarchyCycleGuard.validate({a: b, b: a})
        assert exc.value.code == WMSErrorCode.HIERARCHY_CYCLE

    def test_validate_move_to_self_rejected(self) -> None:
        a = uuid4()
        with pytest.raises(WMSError) as exc:
            HierarchyCycleGuard.validate_move({a: None}, a, a)
        assert exc.value.code == WMSErrorCode.HIERARCHY_CYCLE

    def test_validate_move_to_descendant_rejected(self) -> None:
        a, b = uuid4(), uuid4()
        parent_map = {a: None, b: a}
        with pytest.raises(WMSError) as exc:
            HierarchyCycleGuard.validate_move(parent_map, a, b)
        assert exc.value.code == WMSErrorCode.HIERARCHY_CYCLE

    def test_validate_move_to_unrelated_node_allowed(self) -> None:
        a, b, c = uuid4(), uuid4(), uuid4()
        parent_map = {a: None, b: None, c: None}
        HierarchyCycleGuard.validate_move(parent_map, a, b)

    def test_validate_move_to_root_allowed(self) -> None:
        a, b = uuid4(), uuid4()
        parent_map = {a: b, b: None}
        HierarchyCycleGuard.validate_move(parent_map, a, None)


class ZoneFunctionGuardTest:
    """ZoneFunctionGuard 作业类型与库区功能匹配校验测试。"""

    def test_receiving_matches_receiving_zone(self) -> None:
        assert ZoneFunctionGuard.is_match(ZoneFunction.RECEIVING, OperationType.RECEIVING) is True

    def test_receiving_matches_qc_zone(self) -> None:
        assert ZoneFunctionGuard.is_match(ZoneFunction.QC, OperationType.RECEIVING) is True

    def test_receiving_rejects_storage_zone(self) -> None:
        assert ZoneFunctionGuard.is_match(ZoneFunction.STORAGE, OperationType.RECEIVING) is False

    def test_putaway_requires_storage_zone(self) -> None:
        assert ZoneFunctionGuard.is_match(ZoneFunction.STORAGE, OperationType.PUTAWAY) is True
        assert ZoneFunctionGuard.is_match(ZoneFunction.RECEIVING, OperationType.PUTAWAY) is False
        assert ZoneFunctionGuard.is_match(ZoneFunction.PICKING, OperationType.PUTAWAY) is False

    def test_picking_matches_picking_and_storage(self) -> None:
        assert ZoneFunctionGuard.is_match(ZoneFunction.PICKING, OperationType.PICKING) is True
        assert ZoneFunctionGuard.is_match(ZoneFunction.STORAGE, OperationType.PICKING) is True
        assert ZoneFunctionGuard.is_match(ZoneFunction.SHIPPING, OperationType.PICKING) is False

    def test_shipping_requires_shipping_zone(self) -> None:
        assert ZoneFunctionGuard.is_match(ZoneFunction.SHIPPING, OperationType.SHIPPING) is True
        assert ZoneFunctionGuard.is_match(ZoneFunction.STORAGE, OperationType.SHIPPING) is False

    def test_qc_requires_qc_zone(self) -> None:
        assert ZoneFunctionGuard.is_match(ZoneFunction.QC, OperationType.QC) is True
        assert ZoneFunctionGuard.is_match(ZoneFunction.STORAGE, OperationType.QC) is False

    def test_transfer_accepts_multiple_zones(self) -> None:
        for zf in (ZoneFunction.STORAGE, ZoneFunction.PICKING, ZoneFunction.RECEIVING, ZoneFunction.SHIPPING):
            assert ZoneFunctionGuard.is_match(zf, OperationType.TRANSFER) is True
        assert ZoneFunctionGuard.is_match(ZoneFunction.QC, OperationType.TRANSFER) is False
        assert ZoneFunctionGuard.is_match(ZoneFunction.BLOCKED, OperationType.TRANSFER) is False

    def test_validate_raises_on_mismatch(self) -> None:
        with pytest.raises(WMSError) as exc:
            ZoneFunctionGuard.validate(ZoneFunction.SHIPPING, OperationType.PUTAWAY)
        assert exc.value.code == WMSErrorCode.ZONE_FUNCTION_MISMATCH
        assert exc.value.details["zone_function"] == "shipping"
        assert exc.value.details["operation"] == "putaway"

    def test_validate_passes_on_match(self) -> None:
        ZoneFunctionGuard.validate(ZoneFunction.STORAGE, OperationType.PUTAWAY)

    def test_allowed_operations_for_storage(self) -> None:
        ops = ZoneFunctionGuard.allowed_operations(ZoneFunction.STORAGE)
        op_values = {o.value for o in ops}
        assert "putaway" in op_values
        assert "picking" in op_values
        assert "transfer" in op_values

    def test_allowed_operations_for_shipping(self) -> None:
        ops = ZoneFunctionGuard.allowed_operations(ZoneFunction.SHIPPING)
        op_values = {o.value for o in ops}
        assert op_values == {"shipping", "transfer"}

    def test_allowed_operations_for_blocked_is_empty(self) -> None:
        ops = ZoneFunctionGuard.allowed_operations(ZoneFunction.BLOCKED)
        assert ops == []

    def test_all_operation_types_covered(self) -> None:
        assert len(list(OperationType)) == 6