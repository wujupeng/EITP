"""企业分类聚合根 - 企业级分类，含 tenant_id（租户级隔离）。

支持企业在集团分类基础上增加企业特有分类（spec 5.4.1.2）。
parent_category_level 区分父分类是集团级（group）还是企业级（enterprise）。
"""

from __future__ import annotations

from enum import Enum
from uuid import UUID

from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode


class ParentCategoryLevel(str, Enum):
    GROUP = "group"
    ENTERPRISE = "enterprise"


class EnterpriseCategoryStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class EnterpriseCategoryAggregate(AggregateRoot):
    """企业分类聚合根 - 租户内唯一编码。

    可挂在集团分类下（parent_category_level=group）或企业分类下（parent_category_level=enterprise）。
    """

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        enterprise_category_code: str,
        enterprise_category_name: str,
        level: int = 1,
        parent_category_id: UUID | None = None,
        parent_category_level: ParentCategoryLevel | None = None,
        status: EnterpriseCategoryStatus = EnterpriseCategoryStatus.ACTIVE,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._enterprise_category_code = enterprise_category_code
        self._enterprise_category_name = enterprise_category_name
        self._level = level
        self._parent_category_id = parent_category_id
        self._parent_category_level = parent_category_level
        self._status = status
        self._children: list[EnterpriseCategoryAggregate] = []

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def enterprise_category_code(self) -> str:
        return self._enterprise_category_code

    @property
    def enterprise_category_name(self) -> str:
        return self._enterprise_category_name

    @property
    def level(self) -> int:
        return self._level

    @property
    def parent_category_id(self) -> UUID | None:
        return self._parent_category_id

    @property
    def parent_category_level(self) -> ParentCategoryLevel | None:
        return self._parent_category_level

    @property
    def status(self) -> EnterpriseCategoryStatus:
        return self._status

    @property
    def children(self) -> list[EnterpriseCategoryAggregate]:
        return list(self._children)

    def is_active(self) -> bool:
        return self._status == EnterpriseCategoryStatus.ACTIVE

    def add_child(self, child: EnterpriseCategoryAggregate) -> None:
        if child.tenant_id != self._tenant_id:
            raise MDMError(
                MDMErrorCode.CROSS_TENANT_POLICY_DENIED,
                "子分类租户与父分类租户不一致",
            )
        if child.parent_category_id != self._id.value:
            raise MDMError(
                MDMErrorCode.CATEGORY_MULTI_BELONG_DENIED,
                "子分类 parent_category_id 与当前聚合根不一致",
            )
        child._level = self._level + 1
        child._parent_category_level = ParentCategoryLevel.ENTERPRISE
        self._children.append(child)
        self._touch()

    def validate_no_cycle(self, visited: set[UUID] | None = None) -> None:
        """验证树形结构无循环引用。"""
        if visited is None:
            visited = set()
        current_id = self._id.value
        if current_id in visited:
            raise MDMError(
                MDMErrorCode.CATEGORY_CYCLE,
                f"企业分类 {self._enterprise_category_code} 检测到循环引用",
            )
        visited.add(current_id)
        for child in self._children:
            child.validate_no_cycle(visited)

    def disable(self) -> None:
        if self._status == EnterpriseCategoryStatus.DISABLED:
            return
        self._status = EnterpriseCategoryStatus.DISABLED
        self._touch()

    def enable(self) -> None:
        if self._status == EnterpriseCategoryStatus.ACTIVE:
            return
        self._status = EnterpriseCategoryStatus.ACTIVE
        self._touch()

    def update_name(self, name: str) -> None:
        self._enterprise_category_name = name
        self._touch()