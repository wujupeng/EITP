"""Location 聚合根 - 仓储空间管理的核心库位，扩展 INV-001 LocationConfigAggregate。

LocationConfigAggregate 降级为 INV 内部容量校验值对象，被 WMS LocationAggregate 引用。
"""

from __future__ import annotations

from enum import Enum
from uuid import UUID

from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.domain.warehouse.events.space_changed_event import (
    SpaceAction,
    SpaceChangedEvent,
    SpaceEntityType,
)
from app.domain.warehouse.value_objects.capacity import Capacity, CapacityCheckResult
from app.domain.warehouse.value_objects.coordinate import Coordinate
from app.domain.warehouse.value_objects.location_type_wms import LocationTypeWms
from app.domain.warehouse.value_objects.zone_function import ZoneFunction
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode


class LocationStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class LocationAggregate(AggregateRoot):
    """库位聚合根 - 仓库内的物理存储位置，location_code 在仓库内唯一。

    停用时拒绝新上架与新拣货但保留存量库存。
    """

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        warehouse_id: UUID,
        zone_id: UUID,
        location_code: str,
        location_type: LocationTypeWms = LocationTypeWms.SHELF,
        area_id: UUID | None = None,
        capacity: Capacity | None = None,
        coordinate: Coordinate | None = None,
        status: LocationStatus = LocationStatus.ACTIVE,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._warehouse_id = warehouse_id
        self._zone_id = zone_id
        self._area_id = area_id
        self._location_code = location_code
        self._location_type = location_type
        self._capacity = capacity or Capacity()
        self._coordinate = coordinate or Coordinate()
        self._status = status

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def warehouse_id(self) -> UUID:
        return self._warehouse_id

    @property
    def zone_id(self) -> UUID:
        return self._zone_id

    @property
    def area_id(self) -> UUID | None:
        return self._area_id

    @property
    def location_code(self) -> str:
        return self._location_code

    @property
    def location_type(self) -> LocationTypeWms:
        return self._location_type

    @property
    def capacity(self) -> Capacity:
        return self._capacity

    @property
    def coordinate(self) -> Coordinate:
        return self._coordinate

    @property
    def status(self) -> LocationStatus:
        return self._status

    def is_active(self) -> bool:
        return self._status == LocationStatus.ACTIVE

    def enable(self) -> None:
        if self._status == LocationStatus.ACTIVE:
            return
        before = {"status": self._status.value}
        self._status = LocationStatus.ACTIVE
        self._touch()
        after = {"status": self._status.value}
        self._record_event(
            SpaceChangedEvent(
                tenant_id=self._tenant_id,
                entity_type=SpaceEntityType.LOCATION,
                entity_id=self._id.value,
                action=SpaceAction.ENABLED,
                before_state=before,
                after_state=after,
            )
        )

    def disable(self) -> None:
        if self._status == LocationStatus.INACTIVE:
            return
        before = {"status": self._status.value}
        self._status = LocationStatus.INACTIVE
        self._touch()
        after = {"status": self._status.value}
        self._record_event(
            SpaceChangedEvent(
                tenant_id=self._tenant_id,
                entity_type=SpaceEntityType.LOCATION,
                entity_id=self._id.value,
                action=SpaceAction.DISABLED,
                before_state=before,
                after_state=after,
            )
        )

    def check_capacity(
        self,
        add_qty: float = 0,
        add_weight: float = 0,
        add_volume: float = 0,
        current_qty: float = 0,
        current_weight: float = 0,
        current_volume: float = 0,
    ) -> CapacityCheckResult:
        """校验新增数量/重量/体积是否超出容量限制。"""
        if not self.is_active():
            raise WMSError(
                WMSErrorCode.LOCATION_DISABLED,
                f"库位 {self._location_code} 已停用，拒绝新作业",
            )
        result = self._capacity.check(
            add_qty=add_qty,
            add_weight=add_weight,
            add_volume=add_volume,
            current_qty=current_qty,
            current_weight=current_weight,
            current_volume=current_volume,
        )
        if not result.allowed:
            raise WMSError(
                WMSErrorCode.LOCATION_CAPACITY_EXCEEDED,
                result.message,
                details={"location_code": self._location_code, "exceeded_dims": result.exceeded_dims},
            )
        return result

    def check_zone_function(self, expected: ZoneFunction) -> None:
        """校验库位所属库区的功能是否与期望匹配。"""
        pass

    def update_coordinate(self, coordinate: Coordinate) -> None:
        if not self.is_active():
            raise WMSError(
                WMSErrorCode.LOCATION_DISABLED,
                f"库位 {self._location_code} 已停用，无法更新坐标",
            )
        before = {"coordinate": None}
        self._coordinate = coordinate
        self._touch()
        after = {"coordinate": {"x": coordinate.x, "y": coordinate.y, "z": coordinate.z}}
        self._record_event(
            SpaceChangedEvent(
                tenant_id=self._tenant_id,
                entity_type=SpaceEntityType.LOCATION,
                entity_id=self._id.value,
                action=SpaceAction.UPDATED,
                before_state=before,
                after_state=after,
            )
        )