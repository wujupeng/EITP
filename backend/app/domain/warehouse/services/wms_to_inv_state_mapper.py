"""WMS→INV 状态映射服务 - 将 WMS InventoryStatus 映射到 INV 状态字段。"""

from __future__ import annotations

from app.domain.warehouse.value_objects.inventory_status import (
    InventoryStatus,
    inv_state_field_for,
)


class WmsToInvStateMapper:
    """WMS→INV 状态映射领域服务。

    映射规则（spec 5.2.1.3）：
        AVAILABLE   → on_hand
        IN_QC       → inspection
        BLOCKED     → blocked
        IN_TRANSIT  → in_transit
        QUARANTINED → blocked
        RETURNED    → on_hand（标记 returned）
    """

    @staticmethod
    def to_inv_state_field(wms_status: InventoryStatus) -> str:
        """将 WMS InventoryStatus 映射到 INV 状态字段名。"""
        return inv_state_field_for(wms_status)

    @staticmethod
    def to_inv_delta(wms_status: InventoryStatus, quantity: float) -> dict[str, float]:
        """将 WMS 库存状态与数量映射到 INV 各状态字段的增量。

        Returns:
            dict[str, float] - INV 状态字段名 → 增量
        """
        field = inv_state_field_for(wms_status)
        return {field: quantity}

    @staticmethod
    def is_on_hand_equivalent(wms_status: InventoryStatus) -> bool:
        """WMS 状态是否映射到 INV on_hand（即可用库存）。"""
        return inv_state_field_for(wms_status) == "on_hand"

    @staticmethod
    def is_blocked_equivalent(wms_status: InventoryStatus) -> bool:
        """WMS 状态是否映射到 INV blocked（即不可用库存）。"""
        return inv_state_field_for(wms_status) == "blocked"