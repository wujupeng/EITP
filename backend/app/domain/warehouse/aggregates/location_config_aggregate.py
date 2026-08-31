"""库位配置聚合根 - 引用 MT-001 层级节点，扩展库位类型与容量配置。"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.inventory.value_objects.shared import (
    CapacityEnforceMode,
    LocationType,
    ProductStatus,
)
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import INVError, INVErrorCode


@dataclass(frozen=True)
class CapacityCheckResult:
    allowed: bool
    exceeded: bool
    message: str = ""


_LOCATION_STATE_MAP: dict[LocationType, str] = {
    LocationType.STORAGE: "on_hand",
    LocationType.PICKING: "on_hand",
    LocationType.RECEIVING: "on_hand",
    LocationType.RETURN: "on_hand",
    LocationType.INSPECTION: "inspection",
}


def state_for_location(loc_type: LocationType) -> str:
    return _LOCATION_STATE_MAP.get(loc_type, "on_hand")


class LocationConfigAggregate(AggregateRoot):
    """库位配置聚合根 - 引用 MT-001 HierarchyNode（Location 层级节点）。"""

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        warehouse_id: UUID,
        location_type: LocationType = LocationType.STORAGE,
        capacity: float | None = None,
        capacity_enforce_mode: CapacityEnforceMode = CapacityEnforceMode.WARN,
        status: ProductStatus = ProductStatus.ACTIVE,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._warehouse_id = warehouse_id
        self._location_type = location_type
        self._capacity = capacity
        self._capacity_enforce_mode = capacity_enforce_mode
        self._status = status

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def warehouse_id(self) -> UUID:
        return self._warehouse_id

    @property
    def location_type(self) -> LocationType:
        return self._location_type

    @property
    def capacity(self) -> float | None:
        return self._capacity

    @property
    def capacity_enforce_mode(self) -> CapacityEnforceMode:
        return self._capacity_enforce_mode

    @property
    def status(self) -> ProductStatus:
        return self._status

    def is_active(self) -> bool:
        return self._status == ProductStatus.ACTIVE

    def check_capacity(self, current_qty: float, add_qty: float) -> CapacityCheckResult:
        if self._capacity is None:
            return CapacityCheckResult(allowed=True, exceeded=False)
        total = current_qty + add_qty
        if total <= self._capacity:
            return CapacityCheckResult(allowed=True, exceeded=False)
        if self._capacity_enforce_mode == CapacityEnforceMode.REJECT:
            return CapacityCheckResult(
                allowed=False,
                exceeded=True,
                message=f"库位容量超限: {total} > {self._capacity}",
            )
        return CapacityCheckResult(
            allowed=True,
            exceeded=True,
            message=f"库位容量超限告警: {total} > {self._capacity}",
        )

    def state_field(self) -> str:
        return state_for_location(self._location_type)