"""Bin 聚合根 - 料箱（可选层），bin_code 在库位内唯一。"""

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


class BinStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class BinAggregate(AggregateRoot):
    """料箱聚合根 - 库位内的可选细分容器，bin_code 在库位内唯一。"""

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        location_id: UUID,
        bin_code: str,
        status: BinStatus = BinStatus.ACTIVE,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._location_id = location_id
        self._bin_code = bin_code
        self._status = status

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def location_id(self) -> UUID:
        return self._location_id

    @property
    def bin_code(self) -> str:
        return self._bin_code

    @property
    def status(self) -> BinStatus:
        return self._status

    def is_active(self) -> bool:
        return self._status == BinStatus.ACTIVE

    def enable(self) -> None:
        if self._status == BinStatus.ACTIVE:
            return
        before = {"status": self._status.value}
        self._status = BinStatus.ACTIVE
        self._touch()
        after = {"status": self._status.value}
        self._record_event(
            SpaceChangedEvent(
                tenant_id=self._tenant_id,
                entity_type=SpaceEntityType.BIN,
                entity_id=self._id.value,
                action=SpaceAction.ENABLED,
                before_state=before,
                after_state=after,
            )
        )

    def disable(self) -> None:
        if self._status == BinStatus.INACTIVE:
            return
        before = {"status": self._status.value}
        self._status = BinStatus.INACTIVE
        self._touch()
        after = {"status": self._status.value}
        self._record_event(
            SpaceChangedEvent(
                tenant_id=self._tenant_id,
                entity_type=SpaceEntityType.BIN,
                entity_id=self._id.value,
                action=SpaceAction.DISABLED,
                before_state=before,
                after_state=after,
            )
        )