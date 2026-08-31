"""角色聚合根 - RBAC 角色与权限关联。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from app.interfaces.middleware.error_handler import IAMError, IAMErrorCode


class BuiltinRole(str, Enum):
    PLATFORM_SUPER_ADMIN = "platform_super_admin"
    MULTI_TENANT_ADMIN = "multi_tenant_admin"
    TENANT_ADMIN = "tenant_admin"
    ENTERPRISE_ADMIN = "enterprise_admin"
    BUSINESS_USER = "business_user"


@dataclass
class RoleAggregate:
    """角色聚合根。"""

    id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    role_code: str = ""
    role_name: str = ""
    description: str = ""
    is_builtin: bool = False
    is_active: bool = True
    permission_ids: set[UUID] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_permission(self, permission_id: UUID) -> None:
        self.permission_ids.add(permission_id)
        self._touch()

    def remove_permission(self, permission_id: UUID) -> None:
        if self.is_builtin:
            raise IAMError(
                IAMErrorCode.BUILTIN_ROLE_PROTECTED,
                f"内置角色 {self.role_code} 权限不可修改",
            )
        self.permission_ids.discard(permission_id)
        self._touch()

    def deactivate(self) -> None:
        if self.is_builtin:
            raise IAMError(
                IAMErrorCode.BUILTIN_ROLE_PROTECTED,
                f"内置角色 {self.role_code} 不可停用",
            )
        self.is_active = False
        self._touch()

    def activate(self) -> None:
        self.is_active = True
        self._touch()

    def _touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    @classmethod
    def builtin(cls, tenant_id: UUID, role: BuiltinRole) -> RoleAggregate:
        names = {
            BuiltinRole.PLATFORM_SUPER_ADMIN: "平台超级管理员",
            BuiltinRole.MULTI_TENANT_ADMIN: "多租户管理员",
            BuiltinRole.TENANT_ADMIN: "租户管理员",
            BuiltinRole.ENTERPRISE_ADMIN: "企业管理员",
            BuiltinRole.BUSINESS_USER: "业务用户",
        }
        return cls(
            tenant_id=tenant_id,
            role_code=role.value,
            role_name=names[role],
            is_builtin=True,
        )