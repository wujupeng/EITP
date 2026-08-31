"""集团分类聚合根 - 树形结构，全平台唯一编码，无 tenant_id（集团级）。

禁止循环引用（spec 5.4.1.3）。
"""

from __future__ import annotations

from enum import Enum
from uuid import UUID

from app.domain.group_catalog.events.group_catalog_events import (
    GroupCategoryPublishedEvent,
)
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode


class CategoryStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class GroupCategoryAggregate(AggregateRoot):
    """集团分类聚合根 - 树形结构（parent_category_id 自引用）。

    全平台唯一编码，支持多级分类，无 tenant_id（集团级）。
    """

    def __init__(
        self,
        id: EntityId,
        group_category_code: str,
        group_category_name: str,
        level: int = 1,
        parent_category_id: UUID | None = None,
        status: CategoryStatus = CategoryStatus.ACTIVE,
        published_version: int = 0,
    ) -> None:
        super().__init__(id)
        self._group_category_code = group_category_code
        self._group_category_name = group_category_name
        self._level = level
        self._parent_category_id = parent_category_id
        self._status = status
        self._published_version = published_version
        self._children: list[GroupCategoryAggregate] = []

    @property
    def group_category_code(self) -> str:
        return self._group_category_code

    @property
    def group_category_name(self) -> str:
        return self._group_category_name

    @property
    def level(self) -> int:
        return self._level

    @property
    def parent_category_id(self) -> UUID | None:
        return self._parent_category_id

    @property
    def status(self) -> CategoryStatus:
        return self._status

    @property
    def published_version(self) -> int:
        return self._published_version

    @property
    def children(self) -> list[GroupCategoryAggregate]:
        return list(self._children)

    def is_active(self) -> bool:
        return self._status == CategoryStatus.ACTIVE

    def add_child(self, child: GroupCategoryAggregate) -> None:
        if child.parent_category_id != self._id.value:
            raise MDMError(
                MDMErrorCode.CATEGORY_MULTI_BELONG_DENIED,
                "子分类 parent_category_id 与当前聚合根不一致",
            )
        if child.group_category_code == self._group_category_code:
            raise MDMError(
                MDMErrorCode.CATEGORY_CYCLE,
                "子分类编码与父分类编码重复",
            )
        child._level = self._level + 1
        self._children.append(child)
        self._touch()

    def validate_no_cycle(self, visited: set[UUID] | None = None) -> None:
        """验证树形结构无循环引用（spec 5.4.1.3）。"""
        if visited is None:
            visited = set()
        current_id = self._id.value
        if current_id in visited:
            raise MDMError(
                MDMErrorCode.CATEGORY_CYCLE,
                f"集团分类 {self._group_category_code} 检测到循环引用",
            )
        visited.add(current_id)
        for child in self._children:
            child.validate_no_cycle(visited)

    def disable(self) -> None:
        if self._status == CategoryStatus.DISABLED:
            return
        self._status = CategoryStatus.DISABLED
        self._touch()

    def enable(self) -> None:
        if self._status == CategoryStatus.ACTIVE:
            return
        self._status = CategoryStatus.ACTIVE
        self._touch()

    def publish(self, new_version: int) -> None:
        if new_version <= self._published_version:
            raise MDMError(
                MDMErrorCode.SPEC_INSTANCE_INVALID,
                f"发布版本号 {new_version} 必须大于当前版本 {self._published_version}",
            )
        old_version = self._published_version
        self._published_version = new_version
        self._touch()
        self._record_event(
            GroupCategoryPublishedEvent(
                group_category_id=self._id.value,
                group_category_code=self._group_category_code,
                from_version=old_version,
                to_version=new_version,
            )
        )

    def update_name(self, name: str) -> None:
        self._group_category_name = name
        self._touch()