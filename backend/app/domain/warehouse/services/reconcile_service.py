"""对账服务 - 对比 WMS Inventory Position 与 INV InventoryBalance，发现差异并修复。

红线：INV 是事实源，发现不一致时以 INV 为准修复 WMS。
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.domain_event import DomainEvent
from app.domain.warehouse.events.position_changed_event import WmsInvInconsistentEvent
from app.domain.warehouse.value_objects.inventory_status import InventoryStatus


@dataclass(frozen=True)
class ReconcileDiff:
    """对账差异记录。"""
    tenant_id: UUID
    warehouse_id: UUID
    sku_id: UUID
    location_id: UUID | None
    wms_qty: float
    inv_qty: float
    diff: float
    wms_status: InventoryStatus | None = None
    inv_state_field: str | None = None

    def is_consistent(self) -> bool:
        return abs(self.diff) < 1e-9


@dataclass
class ReconcileResult:
    """对账结果。"""
    tenant_id: UUID
    warehouse_id: UUID
    diffs: list[ReconcileDiff]
    repaired: bool = False

    @property
    def diff_count(self) -> int:
        return len(self.diffs)

    @property
    def has_diff(self) -> bool:
        return len(self.diffs) > 0


class ReconcileService:
    """对账领域服务 - 对比 WMS Position 与 INV Balance，发现差异并修复。

    红线：INV 是事实源，以 INV 为准修复 WMS。
    """

    @staticmethod
    def reconcile(
        tenant_id: UUID,
        warehouse_id: UUID,
        wms_positions: list[tuple[UUID, UUID, float, InventoryStatus]],
        inv_balances: list[tuple[UUID, UUID, float, str]],
    ) -> ReconcileResult:
        """对账 - 对比 WMS Position 与 INV Balance。

        Args:
            wms_positions: [(sku_id, location_id, quantity, inventory_status), ...]
            inv_balances: [(sku_id, location_id, quantity, state_field), ...]

        Returns:
            ReconcileResult - 含差异列表
        """
        wms_map: dict[tuple[UUID, UUID], tuple[float, InventoryStatus]] = {}
        for sku_id, loc_id, qty, status in wms_positions:
            key = (sku_id, loc_id)
            if key in wms_map:
                prev_qty, _ = wms_map[key]
                wms_map[key] = (prev_qty + qty, status)
            else:
                wms_map[key] = (qty, status)

        inv_map: dict[tuple[UUID, UUID], tuple[float, str]] = {}
        for sku_id, loc_id, qty, state_field in inv_balances:
            key = (sku_id, loc_id)
            if key in inv_map:
                prev_qty, _ = inv_map[key]
                inv_map[key] = (prev_qty + qty, state_field)
            else:
                inv_map[key] = (qty, state_field)

        diffs: list[ReconcileDiff] = []
        all_keys = set(wms_map.keys()) | set(inv_map.keys())

        for key in all_keys:
            sku_id, loc_id = key
            wms_qty, wms_status = wms_map.get(key, (0.0, None))
            inv_qty, inv_state = inv_map.get(key, (0.0, None))
            diff = wms_qty - inv_qty
            if abs(diff) >= 1e-9:
                diffs.append(ReconcileDiff(
                    tenant_id=tenant_id,
                    warehouse_id=warehouse_id,
                    sku_id=sku_id,
                    location_id=loc_id,
                    wms_qty=wms_qty,
                    inv_qty=inv_qty,
                    diff=diff,
                    wms_status=wms_status,
                    inv_state_field=inv_state,
                ))

        return ReconcileResult(
            tenant_id=tenant_id,
            warehouse_id=warehouse_id,
            diffs=diffs,
        )

    @staticmethod
    def build_inconsistent_events(result: ReconcileResult) -> list[WmsInvInconsistentEvent]:
        """将对账差异转换为领域事件。"""
        events: list[WmsInvInconsistentEvent] = []
        for diff in result.diffs:
            events.append(WmsInvInconsistentEvent(
                tenant_id=diff.tenant_id,
                warehouse_id=diff.warehouse_id,
                sku_id=diff.sku_id,
                wms_qty=diff.wms_qty,
                inv_qty=diff.inv_qty,
                diff=diff.diff,
                location_id=diff.location_id,
            ))
        return events