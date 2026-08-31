"""Zone 聚合根 - 仓库内库区，具有六种功能分区。"""

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
from app.domain.warehouse.value_objects.zone_function import ZoneFunction
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode


class ZoneStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class ZoneAggregate(AggregateRoot):
    """库区聚合根 - 仓库内的功能分区，zone_code 在仓库内唯一。"""

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        warehouse_id: UUID,
        zone_code: str,
        zone_name: str,
        zone_function: ZoneFunction = ZoneFunction.STORAGE,
        status: ZoneStatus = ZoneStatus.ACTIVE,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._warehouse_id = warehouse_id
        self._zone_code = zone_code
        self._zone_name = zone_name
        self._zone_function = zone_function
        self._status = status

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def warehouse_id(self) -> UUID:
        return self._warehouse_id

    @property
    def zone_code(self) -> str:
        return self._zone_code

    @property
    def zone_name(self) -> str:
        return self._zone_name

    @property
    def zone_function(self) -> ZoneFunction:
        return self._zone_function

    @property
    def status(self) -> ZoneStatus:
        return self._status

    def is_active(self) -> bool:
        return self._status == ZoneStatus.ACTIVE

    def enable(self) -> None:
        if self._status == ZoneStatus.ACTIVE:
            return
        before = {"status": self._status.value}
        self._status = ZoneStatus.ACTIVE
        self._touch()
        after = {"status": self._status.value}
        self._record_event(
            SpaceChangedEvent(
                tenant_id=self._tenant_id,
                entity_type=SpaceEntityType.ZONE,
                entity_id=self._id.value,
                action=SpaceAction.ENABLED,
                before_state=before,
                after_state=after,
            )
        )

    def disable(self) -> None:
        if self._status == ZoneStatus.DISABLED:
            return
        before = {"status": self._status.value}
        self._status = ZoneStatus.DISABLED
        self._touch()
        after = {"status": self._status.value}
        self._record_event(
            SpaceChangedEvent(
                tenant_id=self._tenant_id,
                entity_type=SpaceEntityType.ZONE,
                entity_id=self._id.value,
                action=SpaceAction.DISABLED,
                before_state=before,
                after_state=after,
            )
        )

    def update_name(self, name: str) -> None:
        if not name.strip():
            raise WMSError(
                WMSErrorCode.SERVICE_UNAVAILABLE,
                "库区名称不能为空",
            )
        before = {"zone_name": self._zone_name}
        self._zone_name = name
        self._touch()
        after = {"zone_name": self._zone_name}
        self._record_event(
            SpaceChangedEvent(
                tenant_id=self._tenant_id,
                entity_type=SpaceEntityType.ZONE,
                entity_id=self._id.value,
                action=SpaceAction.UPDATED,
                before_state=before,
                after_state=after,
            )
        )