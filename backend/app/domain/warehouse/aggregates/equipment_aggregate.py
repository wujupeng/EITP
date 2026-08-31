"""Equipment 聚合根 - 作业设备，equipment_code 在仓库内唯一。"""

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
from app.domain.warehouse.value_objects.equipment_type import EquipmentType


class EquipmentStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class EquipmentAggregate(AggregateRoot):
    """作业设备聚合根 - 关联作业任务与执行人，equipment_code 在仓库内唯一。"""

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        warehouse_id: UUID,
        equipment_code: str,
        equipment_type: EquipmentType = EquipmentType.FORKLIFT,
        status: EquipmentStatus = EquipmentStatus.ACTIVE,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._warehouse_id = warehouse_id
        self._equipment_code = equipment_code
        self._equipment_type = equipment_type
        self._status = status
        self._assigned_task_ids: list[UUID] = []
        self._assigned_user_ids: list[UUID] = []

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def warehouse_id(self) -> UUID:
        return self._warehouse_id

    @property
    def equipment_code(self) -> str:
        return self._equipment_code

    @property
    def equipment_type(self) -> EquipmentType:
        return self._equipment_type

    @property
    def status(self) -> EquipmentStatus:
        return self._status

    @property
    def assigned_task_ids(self) -> list[UUID]:
        return list(self._assigned_task_ids)

    @property
    def assigned_user_ids(self) -> list[UUID]:
        return list(self._assigned_user_ids)

    def is_available(self) -> bool:
        return self._status == EquipmentStatus.ACTIVE

    def enable(self) -> None:
        if self._status == EquipmentStatus.ACTIVE:
            return
        before = {"status": self._status.value}
        self._status = EquipmentStatus.ACTIVE
        self._touch()
        after = {"status": self._status.value}
        self._record_event(
            SpaceChangedEvent(
                tenant_id=self._tenant_id,
                entity_type=SpaceEntityType.EQUIPMENT,
                entity_id=self._id.value,
                action=SpaceAction.ENABLED,
                before_state=before,
                after_state=after,
            )
        )

    def disable(self) -> None:
        if self._status == EquipmentStatus.INACTIVE:
            return
        before = {"status": self._status.value}
        self._status = EquipmentStatus.INACTIVE
        self._touch()
        after = {"status": self._status.value}
        self._record_event(
            SpaceChangedEvent(
                tenant_id=self._tenant_id,
                entity_type=SpaceEntityType.EQUIPMENT,
                entity_id=self._id.value,
                action=SpaceAction.DISABLED,
                before_state=before,
                after_state=after,
            )
        )

    def enter_maintenance(self) -> None:
        if self._status == EquipmentStatus.MAINTENANCE:
            return
        before = {"status": self._status.value}
        self._status = EquipmentStatus.MAINTENANCE
        self._touch()
        after = {"status": self._status.value}
        self._record_event(
            SpaceChangedEvent(
                tenant_id=self._tenant_id,
                entity_type=SpaceEntityType.EQUIPMENT,
                entity_id=self._id.value,
                action=SpaceAction.UPDATED,
                before_state=before,
                after_state=after,
            )
        )

    def assign_task(self, task_id: UUID) -> None:
        if not self.is_available():
            return
        if task_id not in self._assigned_task_ids:
            self._assigned_task_ids.append(task_id)
            self._touch()

    def unassign_task(self, task_id: UUID) -> None:
        if task_id in self._assigned_task_ids:
            self._assigned_task_ids.remove(task_id)
            self._touch()

    def assign_user(self, user_id: UUID) -> None:
        if user_id not in self._assigned_user_ids:
            self._assigned_user_ids.append(user_id)
            self._touch()

    def unassign_user(self, user_id: UUID) -> None:
        if user_id in self._assigned_user_ids:
            self._assigned_user_ids.remove(user_id)
            self._touch()