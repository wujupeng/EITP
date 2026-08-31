"""WMS 库存状态枚举 - 六种物理状态，与 INV 六状态量建立映射。"""

from __future__ import annotations

from enum import Enum


class InventoryStatus(str, Enum):
    """WMS 库存物理状态 - 反映货物在仓库中的实际状态。"""
    AVAILABLE = "available"
    IN_QC = "in_qc"
    BLOCKED = "blocked"
    IN_TRANSIT = "in_transit"
    QUARANTINED = "quarantined"
    RETURNED = "returned"


INV_STATE_FIELD_AVAILABLE = "on_hand"
INV_STATE_FIELD_IN_QC = "inspection"
INV_STATE_FIELD_BLOCKED = "blocked"
INV_STATE_FIELD_IN_TRANSIT = "in_transit"
INV_STATE_FIELD_QUARANTINED = "blocked"
INV_STATE_FIELD_RETURNED = "on_hand"

_WMS_TO_INV_STATE_MAP: dict[InventoryStatus, str] = {
    InventoryStatus.AVAILABLE: INV_STATE_FIELD_AVAILABLE,
    InventoryStatus.IN_QC: INV_STATE_FIELD_IN_QC,
    InventoryStatus.BLOCKED: INV_STATE_FIELD_BLOCKED,
    InventoryStatus.IN_TRANSIT: INV_STATE_FIELD_IN_TRANSIT,
    InventoryStatus.QUARANTINED: INV_STATE_FIELD_QUARANTINED,
    InventoryStatus.RETURNED: INV_STATE_FIELD_RETURNED,
}


def inv_state_field_for(wms_status: InventoryStatus) -> str:
    """将 WMS InventoryStatus 映射到 INV 状态字段名。"""
    return _WMS_TO_INV_STATE_MAP[wms_status]


_VALID_TRANSITIONS: dict[InventoryStatus, frozenset[InventoryStatus]] = {
    InventoryStatus.AVAILABLE: frozenset({
        InventoryStatus.IN_QC,
        InventoryStatus.BLOCKED,
        InventoryStatus.IN_TRANSIT,
        InventoryStatus.QUARANTINED,
    }),
    InventoryStatus.IN_QC: frozenset({
        InventoryStatus.AVAILABLE,
        InventoryStatus.QUARANTINED,
        InventoryStatus.RETURNED,
    }),
    InventoryStatus.BLOCKED: frozenset({
        InventoryStatus.AVAILABLE,
        InventoryStatus.QUARANTINED,
    }),
    InventoryStatus.IN_TRANSIT: frozenset({
        InventoryStatus.AVAILABLE,
    }),
    InventoryStatus.QUARANTINED: frozenset({
        InventoryStatus.AVAILABLE,
        InventoryStatus.BLOCKED,
        InventoryStatus.RETURNED,
    }),
    InventoryStatus.RETURNED: frozenset({
        InventoryStatus.AVAILABLE,
        InventoryStatus.BLOCKED,
    }),
}


def is_valid_transition(from_status: InventoryStatus, to_status: InventoryStatus) -> bool:
    """校验状态流转是否合法。"""
    if from_status == to_status:
        return True
    return to_status in _VALID_TRANSITIONS.get(from_status, frozenset())