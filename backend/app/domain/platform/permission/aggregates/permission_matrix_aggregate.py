"""权限矩阵聚合根 - 权限决策数据源。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class PermissionMatrixAggregate:
    """权限矩阵聚合根 - 角色操作权限决策。"""

    entry_id: UUID
    role_id: str
    operation: str
    resource_scope: str
    data_scope: str
    decision: Decision
    approval_status: ApprovalStatus
    approved_by: str | None
    version: int
    effective_at: datetime
    tenant_id: UUID

    @classmethod
    def create(
        cls,
        role_id: str,
        operation: str,
        resource_scope: str,
        data_scope: str,
        decision: Decision,
        tenant_id: UUID,
        version: int = 1,
    ) -> PermissionMatrixAggregate:
        return cls(
            entry_id=uuid4(),
            role_id=role_id,
            operation=operation,
            resource_scope=resource_scope,
            data_scope=data_scope,
            decision=decision,
            approval_status=ApprovalStatus.PENDING,
            approved_by=None,
            version=version,
            effective_at=datetime.now(timezone.utc),
            tenant_id=tenant_id,
        )

    def approve(self, approver: str) -> PermissionMatrixAggregate:
        return _replace(
            self,
            approval_status=ApprovalStatus.APPROVED,
            approved_by=approver,
        )

    def reject(self, approver: str) -> PermissionMatrixAggregate:
        return _replace(
            self,
            approval_status=ApprovalStatus.REJECTED,
            approved_by=approver,
        )

    def is_effective(self) -> bool:
        return self.approval_status == ApprovalStatus.APPROVED


@dataclass(frozen=True)
class MenuTreeAggregate:
    """菜单树聚合根 - 前端菜单结构管理。"""

    menu_id: UUID
    parent_id: UUID | None
    menu_name: str
    menu_path: str | None
    permission_code: str | None
    sort_order: int
    visible: bool
    tenant_id: UUID

    @classmethod
    def create(
        cls,
        menu_name: str,
        tenant_id: UUID,
        parent_id: UUID | None = None,
        menu_path: str | None = None,
        permission_code: str | None = None,
        sort_order: int = 0,
        visible: bool = True,
    ) -> MenuTreeAggregate:
        return cls(
            menu_id=uuid4(),
            parent_id=parent_id,
            menu_name=menu_name,
            menu_path=menu_path,
            permission_code=permission_code,
            sort_order=sort_order,
            visible=visible,
            tenant_id=tenant_id,
        )

    def hide(self) -> MenuTreeAggregate:
        return _replace(self, visible=False)

    def show(self) -> MenuTreeAggregate:
        return _replace(self, visible=True)


def _replace(aggregate: object, **changes: object) -> object:
    from dataclasses import replace
    return replace(aggregate, **changes)