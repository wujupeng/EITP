"""WMS 辅助聚合根、服务与事件补充单元测试。

覆盖 Warehouse/Area/Bin/Equipment/PutawayTask/LocationConfig 聚合根、
TaskClaimGuard/TaskAssignmentService/ReconcileService 服务、RedLineGuard 清单、
以及拣货/移库/发货/收货/上架完成事件，提升 WMS 领域整体覆盖率。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.inventory.value_objects.shared import (
    CapacityEnforceMode,
    LocationType,
    ProductStatus,
)
from app.domain.shared.entity import EntityId
from app.domain.warehouse.aggregates.area_aggregate import AreaAggregate, AreaStatus
from app.domain.warehouse.aggregates.bin_aggregate import BinAggregate, BinStatus
from app.domain.warehouse.aggregates.equipment_aggregate import (
    EquipmentAggregate,
    EquipmentStatus,
)
from app.domain.warehouse.aggregates.location_config_aggregate import (
    LocationConfigAggregate,
    state_for_location,
)
from app.domain.warehouse.aggregates.putaway_task_aggregate import (
    PutawayStatus,
    PutawayTaskAggregate,
)
from app.domain.warehouse.aggregates.warehouse_aggregate import (
    WarehouseAggregate,
    WarehouseStatusEnum,
)
from app.domain.warehouse.events.picking_transfer_shipping_events import (
    PickingCompletedEvent,
    ShippingCompletedEvent,
    TransferCompletedEvent,
)
from app.domain.warehouse.events.receiving_putaway_events import (
    PutawayCompletedEvent,
    ReceivingCompletedEvent,
)
from app.domain.warehouse.services.location_capacity_checker import (
    LocationCapacityChecker,
)
from app.domain.warehouse.services.reconcile_service import (
    ReconcileDiff,
    ReconcileResult,
    ReconcileService,
)
from app.domain.warehouse.services.red_line_guard import (
    FORBIDDEN_PRIVILEGES,
    PROTECTED_TABLES,
    get_code_review_checklist,
)
from app.domain.warehouse.services.task_assignment_service import (
    TaskAssignmentService,
    WorkloadInfo,
)
from app.domain.warehouse.services.task_claim_guard import TaskClaimGuard
from app.domain.warehouse.value_objects.equipment_type import EquipmentType
from app.domain.warehouse.value_objects.task_priority import TaskPriority
from app.domain.warehouse.value_objects.wms_config import WmsConfig
from app.domain.warehouse.value_objects.wms_task_type import WmsTaskType
from app.interfaces.middleware.error_handler import INVError, WMSError, WMSErrorCode


def _make_warehouse(*, status: WarehouseStatusEnum = WarehouseStatusEnum.ACTIVE) -> WarehouseAggregate:
    return WarehouseAggregate(
        id=EntityId.generate(),
        tenant_id=uuid4(),
        warehouse_code="WH-001",
        warehouse_name="主仓",
        status=status,
    )


def _make_task_for_assignment():
    from app.domain.warehouse.aggregates.wms_task_aggregate import WmsTaskAggregate
    return WmsTaskAggregate(
        id=EntityId.generate(),
        tenant_id=uuid4(),
        task_type=WmsTaskType.RECEIVING,
        document_id=uuid4(),
        document_type="purchase_order",
        priority=TaskPriority.MEDIUM,
    )


class WarehouseAggregateTest:
    """WarehouseAggregate 仓库聚合根测试。"""

    def test_construction(self) -> None:
        wh = _make_warehouse()
        assert wh.warehouse_code == "WH-001"
        assert wh.warehouse_name == "主仓"
        assert wh.is_active() is True
        assert isinstance(wh.wms_config, WmsConfig)

    def test_enable_disable(self) -> None:
        wh = _make_warehouse()
        wh.disable()
        assert wh.status == WarehouseStatusEnum.DISABLED
        assert wh.is_active() is False
        wh.enable()
        assert wh.status == WarehouseStatusEnum.ACTIVE

    def test_disable_idempotent(self) -> None:
        wh = _make_warehouse(status=WarehouseStatusEnum.DISABLED)
        wh.disable()
        assert wh.status == WarehouseStatusEnum.DISABLED

    def test_update_config(self) -> None:
        wh = _make_warehouse()
        new_config = WmsConfig()
        wh.update_config(new_config)
        assert wh.wms_config is new_config

    def test_update_config_rejected_when_disabled(self) -> None:
        wh = _make_warehouse(status=WarehouseStatusEnum.DISABLED)
        with pytest.raises(WMSError) as exc:
            wh.update_config(WmsConfig())
        assert exc.value.code == WMSErrorCode.WAREHOUSE_DISABLED

    def test_update_name(self) -> None:
        wh = _make_warehouse()
        wh.update_name("新仓")
        assert wh.warehouse_name == "新仓"

    def test_update_name_rejects_empty(self) -> None:
        wh = _make_warehouse()
        with pytest.raises(WMSError) as exc:
            wh.update_name("  ")
        assert exc.value.code == WMSErrorCode.SERVICE_UNAVAILABLE


class AreaAggregateTest:
    """AreaAggregate 区域聚合根测试。"""

    def _make_area(self, *, status: AreaStatus = AreaStatus.ACTIVE) -> AreaAggregate:
        return AreaAggregate(
            id=EntityId.generate(),
            tenant_id=uuid4(),
            zone_id=uuid4(),
            area_code="AREA-001",
            area_name="A区",
            status=status,
        )

    def test_construction(self) -> None:
        area = self._make_area()
        assert area.area_code == "AREA-001"
        assert area.is_active() is True

    def test_enable_disable(self) -> None:
        area = self._make_area()
        area.disable()
        assert area.status == AreaStatus.DISABLED
        area.enable()
        assert area.status == AreaStatus.ACTIVE

    def test_update_name(self) -> None:
        area = self._make_area()
        area.update_name("B区")
        assert area.area_name == "B区"

    def test_update_name_rejects_empty(self) -> None:
        area = self._make_area()
        with pytest.raises(WMSError) as exc:
            area.update_name("")
        assert exc.value.code == WMSErrorCode.SERVICE_UNAVAILABLE


class BinAggregateTest:
    """BinAggregate 料箱聚合根测试。"""

    def _make_bin(self, *, status: BinStatus = BinStatus.ACTIVE) -> BinAggregate:
        return BinAggregate(
            id=EntityId.generate(),
            tenant_id=uuid4(),
            location_id=uuid4(),
            bin_code="BIN-001",
            status=status,
        )

    def test_construction(self) -> None:
        b = self._make_bin()
        assert b.bin_code == "BIN-001"
        assert b.is_active() is True

    def test_enable_disable(self) -> None:
        b = self._make_bin()
        b.disable()
        assert b.status == BinStatus.INACTIVE
        b.enable()
        assert b.status == BinStatus.ACTIVE


class EquipmentTypeTest:
    """EquipmentType 设备类型枚举测试。"""

    def test_all_types_present(self) -> None:
        expected = {"forklift", "pda", "scanner", "conveyor", "agv"}
        actual = {t.value for t in EquipmentType}
        assert actual == expected


class EquipmentAggregateTest:
    """EquipmentAggregate 设备聚合根测试。"""

    def _make_equipment(
        self, *, status: EquipmentStatus = EquipmentStatus.ACTIVE
    ) -> EquipmentAggregate:
        return EquipmentAggregate(
            id=EntityId.generate(),
            tenant_id=uuid4(),
            warehouse_id=uuid4(),
            equipment_code="EQ-001",
            equipment_type=EquipmentType.FORKLIFT,
            status=status,
        )

    def test_construction(self) -> None:
        eq = self._make_equipment()
        assert eq.equipment_code == "EQ-001"
        assert eq.equipment_type == EquipmentType.FORKLIFT
        assert eq.is_available() is True
        assert eq.assigned_task_ids == []
        assert eq.assigned_user_ids == []

    def test_enable_disable(self) -> None:
        eq = self._make_equipment()
        eq.disable()
        assert eq.status == EquipmentStatus.INACTIVE
        eq.enable()
        assert eq.status == EquipmentStatus.ACTIVE

    def test_enter_maintenance(self) -> None:
        eq = self._make_equipment()
        eq.enter_maintenance()
        assert eq.status == EquipmentStatus.MAINTENANCE

    def test_enter_maintenance_idempotent(self) -> None:
        eq = self._make_equipment(status=EquipmentStatus.MAINTENANCE)
        eq.enter_maintenance()
        assert eq.status == EquipmentStatus.MAINTENANCE

    def test_assign_task_when_available(self) -> None:
        eq = self._make_equipment()
        task_id = uuid4()
        eq.assign_task(task_id)
        assert task_id in eq.assigned_task_ids

    def test_assign_task_skipped_when_unavailable(self) -> None:
        eq = self._make_equipment(status=EquipmentStatus.MAINTENANCE)
        task_id = uuid4()
        eq.assign_task(task_id)
        assert task_id not in eq.assigned_task_ids

    def test_assign_task_idempotent(self) -> None:
        eq = self._make_equipment()
        task_id = uuid4()
        eq.assign_task(task_id)
        eq.assign_task(task_id)
        assert eq.assigned_task_ids.count(task_id) == 1

    def test_unassign_task(self) -> None:
        eq = self._make_equipment()
        task_id = uuid4()
        eq.assign_task(task_id)
        eq.unassign_task(task_id)
        assert task_id not in eq.assigned_task_ids

    def test_assign_unassign_user(self) -> None:
        eq = self._make_equipment()
        user_id = uuid4()
        eq.assign_user(user_id)
        assert user_id in eq.assigned_user_ids
        eq.unassign_user(user_id)
        assert user_id not in eq.assigned_user_ids


class PutawayTaskAggregateTest:
    """PutawayTaskAggregate 上架任务聚合根测试。"""

    def _make_putaway(
        self, *, target_location_id: uuid4 | None = None
    ) -> PutawayTaskAggregate:
        return PutawayTaskAggregate(
            id=EntityId.generate(),
            tenant_id=uuid4(),
            source_location_id=uuid4(),
            sku_id=uuid4(),
            quantity=100,
            source_document_id=uuid4(),
            target_location_id=target_location_id,
        )

    def test_initial_status_pending_without_target(self) -> None:
        task = self._make_putaway()
        assert task.status == PutawayStatus.PENDING
        assert task.target_location_id is None

    def test_initial_status_target_set_with_target(self) -> None:
        loc = uuid4()
        task = self._make_putaway(target_location_id=loc)
        assert task.status == PutawayStatus.TARGET_SET
        assert task.target_location_id == loc

    def test_set_target_location(self) -> None:
        task = self._make_putaway()
        loc = uuid4()
        task.set_target_location(loc)
        assert task.status == PutawayStatus.TARGET_SET
        assert task.target_location_id == loc

    def test_set_target_rejected_after_execute(self) -> None:
        task = self._make_putaway(target_location_id=uuid4())
        task.execute()
        with pytest.raises(WMSError) as exc:
            task.set_target_location(uuid4())
        assert exc.value.code == WMSErrorCode.PUTAWAY_ALREADY_COMPLETED

    def test_execute_full(self) -> None:
        task = self._make_putaway(target_location_id=uuid4())
        task.execute()
        assert task.status == PutawayStatus.EXECUTING
        assert task.putaway_quantity == 100

    def test_execute_partial(self) -> None:
        task = self._make_putaway(target_location_id=uuid4())
        task.execute(putaway_qty=40)
        assert task.putaway_quantity == 40
        assert task.status == PutawayStatus.EXECUTING
        assert task.remaining_quantity == 60

    def test_execute_rejects_second_call_after_executing(self) -> None:
        task = self._make_putaway(target_location_id=uuid4())
        task.execute(putaway_qty=40)
        with pytest.raises(WMSError) as exc:
            task.execute(putaway_qty=60)
        assert exc.value.code == WMSErrorCode.PUTAWAY_LOCATION_DISABLED

    def test_execute_rejected_without_target(self) -> None:
        task = self._make_putaway()
        with pytest.raises(WMSError) as exc:
            task.execute()
        assert exc.value.code == WMSErrorCode.PUTAWAY_LOCATION_DISABLED

    def test_execute_rejects_negative(self) -> None:
        task = self._make_putaway(target_location_id=uuid4())
        with pytest.raises(WMSError) as exc:
            task.execute(putaway_qty=-1)
        assert exc.value.code == WMSErrorCode.SERVICE_UNAVAILABLE

    def test_execute_rejects_excess(self) -> None:
        task = self._make_putaway(target_location_id=uuid4())
        with pytest.raises(WMSError) as exc:
            task.execute(putaway_qty=101)
        assert exc.value.code == WMSErrorCode.PUTAWAY_CAPACITY_EXCEEDED

    def test_complete(self) -> None:
        task = self._make_putaway(target_location_id=uuid4())
        task.execute()
        task.complete()
        assert task.status == PutawayStatus.COMPLETED

    def test_complete_rejected_before_execute(self) -> None:
        task = self._make_putaway(target_location_id=uuid4())
        with pytest.raises(WMSError) as exc:
            task.complete()
        assert exc.value.code == WMSErrorCode.PUTAWAY_ALREADY_COMPLETED

    def test_cancel(self) -> None:
        task = self._make_putaway()
        task.cancel()
        assert task.status == PutawayStatus.CANCELLED

    def test_cancel_rejected_when_completed(self) -> None:
        task = self._make_putaway(target_location_id=uuid4())
        task.execute()
        task.complete()
        with pytest.raises(WMSError) as exc:
            task.cancel()
        assert exc.value.code == WMSErrorCode.PUTAWAY_ALREADY_COMPLETED

    def test_remaining_quantity(self) -> None:
        task = self._make_putaway(target_location_id=uuid4())
        task.execute(putaway_qty=30)
        assert task.remaining_quantity == 70


class LocationConfigAggregateTest:
    """LocationConfigAggregate 库位配置聚合根测试。"""

    def _make_config(
        self,
        *,
        capacity: float | None = 100,
        mode: CapacityEnforceMode = CapacityEnforceMode.WARN,
    ) -> LocationConfigAggregate:
        return LocationConfigAggregate(
            id=EntityId.generate(),
            tenant_id=uuid4(),
            warehouse_id=uuid4(),
            capacity=capacity,
            capacity_enforce_mode=mode,
        )

    def test_construction(self) -> None:
        loc = self._make_config()
        assert loc.capacity == 100
        assert loc.is_active() is True

    def test_check_capacity_within_limit(self) -> None:
        loc = self._make_config(capacity=100)
        result = loc.check_capacity(current_qty=30, add_qty=50)
        assert result.allowed is True
        assert result.exceeded is False

    def test_check_capacity_unlimited_when_none(self) -> None:
        loc = self._make_config(capacity=None)
        result = loc.check_capacity(current_qty=999, add_qty=999)
        assert result.allowed is True

    def test_check_capacity_warn_mode(self) -> None:
        loc = self._make_config(capacity=100, mode=CapacityEnforceMode.WARN)
        result = loc.check_capacity(current_qty=80, add_qty=30)
        assert result.exceeded is True
        assert result.allowed is True

    def test_check_capacity_reject_mode(self) -> None:
        loc = self._make_config(capacity=100, mode=CapacityEnforceMode.REJECT)
        result = loc.check_capacity(current_qty=80, add_qty=30)
        assert result.exceeded is True
        assert result.allowed is False

    def test_state_field_mapping(self) -> None:
        loc = LocationConfigAggregate(
            id=EntityId.generate(),
            tenant_id=uuid4(),
            warehouse_id=uuid4(),
            location_type=LocationType.INSPECTION,
        )
        assert loc.state_field() == "inspection"

    def test_state_for_location_function(self) -> None:
        assert state_for_location(LocationType.STORAGE) == "on_hand"
        assert state_for_location(LocationType.INSPECTION) == "inspection"


class LocationCapacityCheckerTest:
    """LocationCapacityChecker 库位容量校验器测试。"""

    def test_check_passes(self) -> None:
        loc = LocationConfigAggregate(
            id=EntityId.generate(),
            tenant_id=uuid4(),
            warehouse_id=uuid4(),
            capacity=100,
            capacity_enforce_mode=CapacityEnforceMode.REJECT,
        )
        checker = LocationCapacityChecker()
        result = checker.check(loc, current_qty=30, add_qty=50)
        assert result.allowed is True

    def test_check_raises_on_reject(self) -> None:
        loc = LocationConfigAggregate(
            id=EntityId.generate(),
            tenant_id=uuid4(),
            warehouse_id=uuid4(),
            capacity=100,
            capacity_enforce_mode=CapacityEnforceMode.REJECT,
        )
        checker = LocationCapacityChecker()
        with pytest.raises(INVError):
            checker.check(loc, current_qty=80, add_qty=30)


class TaskClaimGuardTest:
    """TaskClaimGuard 任务领取越权校验测试。"""

    def test_can_claim_when_assignee_none(self) -> None:
        assert TaskClaimGuard.can_claim(None, uuid4()) is True

    def test_can_claim_when_match(self) -> None:
        assignee = uuid4()
        assert TaskClaimGuard.can_claim(assignee, assignee) is True

    def test_can_claim_rejects_mismatch(self) -> None:
        assert TaskClaimGuard.can_claim(uuid4(), uuid4()) is False

    def test_validate_claim_passes(self) -> None:
        assignee = uuid4()
        TaskClaimGuard.validate_claim(assignee, assignee, uuid4())

    def test_validate_claim_raises_on_mismatch(self) -> None:
        with pytest.raises(WMSError) as exc:
            TaskClaimGuard.validate_claim(uuid4(), uuid4(), uuid4())
        assert exc.value.code == WMSErrorCode.TASK_ASSIGNMENT_DENIED


class TaskAssignmentServiceTest:
    """TaskAssignmentService 任务分配服务测试。"""

    def test_manual_assign(self) -> None:
        task = _make_task_for_assignment()
        assignee = uuid4()
        result = TaskAssignmentService.manual_assign(task, assignee)
        assert result.assignee_id == assignee

    def test_auto_assign_picks_least_workload(self) -> None:
        task = _make_task_for_assignment()
        busy = WorkloadInfo(user_id=uuid4(), active_task_count=10, avg_completion_ms=5000)
        idle = WorkloadInfo(user_id=uuid4(), active_task_count=1, avg_completion_ms=1000)
        result = TaskAssignmentService.auto_assign(task, [busy, idle])
        assert result.assignee_id == idle.user_id

    def test_auto_assign_tiebreak_by_completion_time(self) -> None:
        task = _make_task_for_assignment()
        a = WorkloadInfo(user_id=uuid4(), active_task_count=5, avg_completion_ms=3000)
        b = WorkloadInfo(user_id=uuid4(), active_task_count=5, avg_completion_ms=1000)
        result = TaskAssignmentService.auto_assign(task, [a, b])
        assert result.assignee_id == b.user_id

    def test_auto_assign_rejects_empty_candidates(self) -> None:
        task = _make_task_for_assignment()
        with pytest.raises(ValueError):
            TaskAssignmentService.auto_assign(task, [])

    def test_reassign(self) -> None:
        task = _make_task_for_assignment()
        first = uuid4()
        TaskAssignmentService.manual_assign(task, first)
        second = uuid4()
        result = TaskAssignmentService.reassign(task, second)
        assert result.assignee_id == second


class RedLineGuardTest:
    """RedLineGuard 红线防护测试。"""

    def test_protected_tables_defined(self) -> None:
        assert "inv_inventory_ledger" in PROTECTED_TABLES
        assert "inv_inventory_balance" in PROTECTED_TABLES
        assert "inv_inventory_reservation" in PROTECTED_TABLES

    def test_forbidden_privileges_defined(self) -> None:
        assert "INSERT" in FORBIDDEN_PRIVILEGES
        assert "UPDATE" in FORBIDDEN_PRIVILEGES
        assert "DELETE" in FORBIDDEN_PRIVILEGES

    def test_code_review_checklist_non_empty(self) -> None:
        checklist = get_code_review_checklist()
        assert len(checklist) > 0
        assert any("inv_" in item for item in checklist)


class ReconcileServiceTest:
    """ReconcileService 对账服务测试。"""

    def test_reconcile_no_diff_when_consistent(self) -> None:
        tenant_id = uuid4()
        wh_id = uuid4()
        sku_id = uuid4()
        loc_id = uuid4()
        wms_positions = [(sku_id, loc_id, 100.0, __import__(
            "app.domain.warehouse.value_objects.inventory_status", fromlist=["InventoryStatus"]
        ).InventoryStatus.AVAILABLE)]
        inv_balances = [(sku_id, loc_id, 100.0, "on_hand")]
        result = ReconcileService.reconcile(tenant_id, wh_id, wms_positions, inv_balances)
        assert result.has_diff is False
        assert result.diff_count == 0

    def test_reconcile_detects_qty_diff(self) -> None:
        from app.domain.warehouse.value_objects.inventory_status import InventoryStatus
        tenant_id = uuid4()
        wh_id = uuid4()
        sku_id = uuid4()
        loc_id = uuid4()
        wms_positions = [(sku_id, loc_id, 100.0, InventoryStatus.AVAILABLE)]
        inv_balances = [(sku_id, loc_id, 80.0, "on_hand")]
        result = ReconcileService.reconcile(tenant_id, wh_id, wms_positions, inv_balances)
        assert result.has_diff is True
        assert result.diff_count == 1
        assert result.diffs[0].diff == 20.0

    def test_reconcile_detects_missing_in_inv(self) -> None:
        from app.domain.warehouse.value_objects.inventory_status import InventoryStatus
        tenant_id = uuid4()
        wh_id = uuid4()
        sku_id = uuid4()
        loc_id = uuid4()
        wms_positions = [(sku_id, loc_id, 50.0, InventoryStatus.AVAILABLE)]
        inv_balances: list = []
        result = ReconcileService.reconcile(tenant_id, wh_id, wms_positions, inv_balances)
        assert result.diff_count == 1
        assert result.diffs[0].wms_qty == 50.0
        assert result.diffs[0].inv_qty == 0.0

    def test_reconcile_detects_missing_in_wms(self) -> None:
        tenant_id = uuid4()
        wh_id = uuid4()
        sku_id = uuid4()
        loc_id = uuid4()
        wms_positions: list = []
        inv_balances = [(sku_id, loc_id, 50.0, "on_hand")]
        result = ReconcileService.reconcile(tenant_id, wh_id, wms_positions, inv_balances)
        assert result.diff_count == 1
        assert result.diffs[0].diff == -50.0

    def test_reconcile_aggregates_duplicate_keys(self) -> None:
        from app.domain.warehouse.value_objects.inventory_status import InventoryStatus
        tenant_id = uuid4()
        wh_id = uuid4()
        sku_id = uuid4()
        loc_id = uuid4()
        wms_positions = [
            (sku_id, loc_id, 30.0, InventoryStatus.AVAILABLE),
            (sku_id, loc_id, 40.0, InventoryStatus.AVAILABLE),
        ]
        inv_balances = [(sku_id, loc_id, 70.0, "on_hand")]
        result = ReconcileService.reconcile(tenant_id, wh_id, wms_positions, inv_balances)
        assert result.has_diff is False

    def test_build_inconsistent_events(self) -> None:
        from app.domain.warehouse.value_objects.inventory_status import InventoryStatus
        tenant_id = uuid4()
        wh_id = uuid4()
        sku_id = uuid4()
        loc_id = uuid4()
        wms_positions = [(sku_id, loc_id, 100.0, InventoryStatus.AVAILABLE)]
        inv_balances = [(sku_id, loc_id, 80.0, "on_hand")]
        result = ReconcileService.reconcile(tenant_id, wh_id, wms_positions, inv_balances)
        events = ReconcileService.build_inconsistent_events(result)
        assert len(events) == 1
        assert events[0].diff == 20.0

    def test_reconcile_diff_is_consistent(self) -> None:
        diff = ReconcileDiff(
            tenant_id=uuid4(),
            warehouse_id=uuid4(),
            sku_id=uuid4(),
            location_id=None,
            wms_qty=100.0,
            inv_qty=100.0,
            diff=0.0,
        )
        assert diff.is_consistent() is True

    def test_reconcile_diff_not_consistent(self) -> None:
        diff = ReconcileDiff(
            tenant_id=uuid4(),
            warehouse_id=uuid4(),
            sku_id=uuid4(),
            location_id=None,
            wms_qty=100.0,
            inv_qty=80.0,
            diff=20.0,
        )
        assert diff.is_consistent() is False


class WmsDomainEventsTest:
    """WMS 领域事件构造测试。"""

    def test_picking_completed_event(self) -> None:
        event = PickingCompletedEvent(
            tenant_id=uuid4(),
            picking_task_id=uuid4(),
            source_order_id=uuid4(),
            inv_transaction_ids=[uuid4()],
        )
        assert event.inv_transaction_ids is not None

    def test_transfer_completed_event(self) -> None:
        event = TransferCompletedEvent(
            tenant_id=uuid4(),
            transfer_order_id=uuid4(),
            warehouse_id=uuid4(),
            inv_transaction_ids=[uuid4()],
        )
        assert event.warehouse_id is not None

    def test_shipping_completed_event(self) -> None:
        event = ShippingCompletedEvent(
            tenant_id=uuid4(),
            shipping_order_id=uuid4(),
            source_order_id=uuid4(),
            logistics_no="SF001",
            logistics_company="顺丰",
            inv_transaction_ids=[uuid4()],
        )
        assert event.logistics_no == "SF001"

    def test_receiving_completed_event(self) -> None:
        event = ReceivingCompletedEvent(
            tenant_id=uuid4(),
            receiving_id=uuid4(),
            sku_id=uuid4(),
            quantity=100.0,
            warehouse_id=uuid4(),
            location_id=uuid4(),
            inv_transaction_ids=[uuid4()],
        )
        assert event.quantity == 100.0

    def test_putaway_completed_event(self) -> None:
        event = PutawayCompletedEvent(
            tenant_id=uuid4(),
            putaway_task_id=uuid4(),
            sku_id=uuid4(),
            quantity=50.0,
            target_location_id=uuid4(),
            inv_transaction_ids=[uuid4()],
        )
        assert event.quantity == 50.0