"""Area 聚合根 - 库区内区域，area_code 在库区内唯一。"""

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
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode


class AreaStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class AreaAggregate(AggregateRoot):
    """区域聚合根 - 库区内的逻辑分区，area_code 在库区内唯一。"""

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        zone_id: UUID,
        area_code: str,
        area_name: str,
        status: AreaStatus = AreaStatus.ACTIVE,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._zone_id = zone_id
        self._area_code = area_code
        self._area_name = area_name
        self._status = status

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def zone_id(self) -> UUID:
        return self._zone_id

    @property
    def area_code(self) -> str:
        return self._area_code

    @property
    def area_name(self) -> str:
        return self._area_name

    @property
    def status(self) -> AreaStatus:
        return self._status

    def is_active(self) -> bool:
        return self._status == AreaStatus.ACTIVE

    def enable(self) -> None:
        if self._status == AreaStatus.ACTIVE:
            return
        before = {"status": self._status.value}
        self._status = AreaStatus.ACTIVE
        self._touch()
        after = {"status": self._status.value}
        self._record_event(
            SpaceChangedEvent(
                tenant_id=self._tenant_id,
                entity_type=SpaceEntityType.AREA,
                entity_id=self._id.value,
                action=SpaceAction.ENABLED,
                before_state=before,
                after_state=after,
            )
        )

    def disable(self) -> None:
        if self._status == AreaStatus.DISABLED:
            return
        before = {"status": self._status.value}
        self._status = AreaStatus.DISABLED
        self._touch()
        after = {"status": self._status.value}
        self._record_event(
            SpaceChangedEvent(
                tenant_id=self._tenant_id,
                entity_type=SpaceEntityType.AREA,
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
                "区域名称不能为空",
            )
        before = {"area_name": self._area_name}
        self._area_name = name
        self._touch()
        after = {"area_name": self._area_name}
        self._record_event(
            SpaceChangedEvent(
                tenant_id=self._tenant_id,
                entity_type=SpaceEntityType.AREA,
                entity_id=self._id.value,
                action=SpaceAction.UPDATED,
                before_state=before,
                after_state=after,
            )
        )