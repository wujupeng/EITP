"""层级节点实体与层级类型枚举 - 七层组织层级模型。

Platform → Tenant → Enterprise → Organization → Site → Warehouse → Location
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from app.domain.shared.entity import Entity, EntityId


class HierarchyLevel(Enum):
    """层级类型枚举 - 七层组织层级。"""

    PLATFORM = 1
    TENANT = 2
    ENTERPRISE = 3
    ORGANIZATION = 4
    SITE = 5
    WAREHOUSE = 6
    LOCATION = 7

    @classmethod
    def max_depth(cls) -> int:
        return 7


@dataclass(frozen=True)
class HierarchyPath:
    """层级路径值对象 - 从根到当前节点的祖先链。"""

    ancestor_ids: tuple[UUID, ...]

    @property
    def depth(self) -> int:
        return len(self.ancestor_ids)


class HierarchyNode(Entity):
    """层级节点实体 - 具有层级类型、父级引用与活跃状态。

    禁止贫血模型：封装 disable()、is_active() 行为。
    """

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        level: HierarchyLevel,
        name: str,
        parent_id: EntityId | None = None,
        is_active: bool = True,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._level = level
        self._name = name
        self._parent_id = parent_id
        self._is_active = is_active

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def level(self) -> HierarchyLevel:
        return self._level

    @property
    def name(self) -> str:
        return self._name

    @property
    def parent_id(self) -> EntityId | None:
        return self._parent_id

    @property
    def is_active(self) -> bool:
        return self._is_active

    def disable(self) -> None:
        """停用本节点。"""
        if self._is_active:
            self._is_active = False
            self._touch()

    def enable(self) -> None:
        """启用本节点。"""
        if not self._is_active:
            self._is_active = True
            self._touch()

    def rename(self, name: str) -> None:
        """重命名节点。"""
        if not name:
            raise ValueError("节点名称不能为空")
        self._name = name
        self._touch()