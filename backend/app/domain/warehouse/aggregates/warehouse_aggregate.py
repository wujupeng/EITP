"""Warehouse 聚合根 - 仓储空间管理的顶层聚合，复用 MT-001 HierarchyNode。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.domain.warehouse.events.space_changed_event import (
    SpaceAction,
    SpaceChangedEvent,
    SpaceEntityType,
)
from app.domain.warehouse.value_objects.wms_config import WmsConfig
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode


class WarehouseStatusEnum(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class WarehouseAggregate(AggregateRoot):
    """仓库聚合根 - 复用 MT-001 HierarchyNode（Warehouse 层级节点），叠加 WMS 仓储策略配置。

    不重新创建层级树，仅持有 warehouse_id（对应 HierarchyNode 的 id）和 WMS 特有配置。
    """

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        warehouse_code: str,
        warehouse_name: str,
        hierarchy_node_id: UUID | None = None,
        address: str | None = None,
        status: WarehouseStatusEnum = WarehouseStatusEnum.ACTIVE,
        wms_config: WmsConfig | None = None,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._warehouse_code = warehouse_code
        self._warehouse_name = warehouse_name
        self._hierarchy_node_id = hierarchy_node_id
        self._address = address
        self._status = status
        self._wms_config = wms_config or WmsConfig()

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def warehouse_code(self) -> str:
        return self._warehouse_code

    @property
    def warehouse_name(self) -> str:
        return self._warehouse_name

    @property
    def hierarchy_node_id(self) -> UUID | None:
        return self._hierarchy_node_id

    @property
    def address(self) -> str | None:
        return self._address

    @property
    def status(self) -> WarehouseStatusEnum:
        return self._status

    @property
    def wms_config(self) -> WmsConfig:
        return self._wms_config

    def is_active(self) -> bool:
        return self._status == WarehouseStatusEnum.ACTIVE

    def enable(self) -> None:
        if self._status == WarehouseStatusEnum.ACTIVE:
            return
        before = {"status": self._status.value}
        self._status = WarehouseStatusEnum.ACTIVE
        self._touch()
        after = {"status": self._status.value}
        self._record_event(
            SpaceChangedEvent(
                tenant_id=self._tenant_id,
                entity_type=SpaceEntityType.WAREHOUSE,
                entity_id=self._id.value,
                action=SpaceAction.ENABLED,
                before_state=before,
                after_state=after,
            )
        )

    def disable(self) -> None:
        if self._status == WarehouseStatusEnum.DISABLED:
            return
        before = {"status": self._status.value}
        self._status = WarehouseStatusEnum.DISABLED
        self._touch()
        after = {"status": self._status.value}
        self._record_event(
            SpaceChangedEvent(
                tenant_id=self._tenant_id,
                entity_type=SpaceEntityType.WAREHOUSE,
                entity_id=self._id.value,
                action=SpaceAction.DISABLED,
                before_state=before,
                after_state=after,
            )
        )

    def update_config(self, config: WmsConfig) -> None:
        if not self.is_active():
            raise WMSError(
                WMSErrorCode.WAREHOUSE_DISABLED,
                "仓库已停用，无法更新配置",
            )
        before = {"wms_config": self._wms_config.__dict__ if hasattr(self._wms_config, "__dict__") else None}
        self._wms_config = config
        self._touch()
        after = {"wms_config": config.__dict__ if hasattr(config, "__dict__") else None}
        self._record_event(
            SpaceChangedEvent(
                tenant_id=self._tenant_id,
                entity_type=SpaceEntityType.WAREHOUSE,
                entity_id=self._id.value,
                action=SpaceAction.UPDATED,
                before_state=before,
                after_state=after,
            )
        )

    def update_name(self, name: str) -> None:
        if not name.strip():
            raise WMSError(
                WMSErrorCode.SERVICE_UNAVAILABLE,
                "仓库名称不能为空",
            )
        before = {"warehouse_name": self._warehouse_name}
        self._warehouse_name = name
        self._touch()
        after = {"warehouse_name": self._warehouse_name}
        self._record_event(
            SpaceChangedEvent(
                tenant_id=self._tenant_id,
                entity_type=SpaceEntityType.WAREHOUSE,
                entity_id=self._id.value,
                action=SpaceAction.UPDATED,
                before_state=before,
                after_state=after,
            )
        )