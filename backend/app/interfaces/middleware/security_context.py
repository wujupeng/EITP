"""Security Context - IAM 安全上下文五元组。

SecurityContext = User + Tenant + Roles + Permissions + DataScope
与 MT-001 TenantContext 协同：TenantContext 退化为 SecurityContext.tenant 子对象。
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID


class AccessMode(str, Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


@dataclass(frozen=True)
class UserIdentity:
    user_id: UUID
    username: str
    account_status: str = "active"
    is_platform_admin: bool = False
    is_tenant_admin: bool = False


@dataclass(frozen=True)
class TenantIdentity:
    tenant_id: UUID
    tenant_status: str = "active"
    data_placement: str = "shared_db"


@dataclass(frozen=True)
class RoleSummary:
    role_id: UUID
    role_code: str
    role_name: str
    is_builtin: bool = False


@dataclass(frozen=True)
class PermissionSummary:
    codes: frozenset[str] = field(default_factory=frozenset)

    def has(self, code: str) -> bool:
        return code in self.codes

    def has_any(self, codes: set[str]) -> bool:
        return bool(self.codes & codes)


@dataclass(frozen=True)
class ResolvedDataScope:
    scope_type: str = "tenant"
    org_ids: frozenset[UUID] = field(default_factory=frozenset)
    warehouse_ids: frozenset[UUID] = field(default_factory=frozenset)
    access_mode: AccessMode = AccessMode.READ

    def is_subset(self, other: ResolvedDataScope) -> bool:
        if self.scope_type == "platform":
            return True
        if other.scope_type == "platform":
            return False
        if self.scope_type != other.scope_type:
            return False
        if not self.org_ids.issubset(other.org_ids):
            return False
        if not self.warehouse_ids.issubset(other.warehouse_ids):
            return False
        return True


_security_context: ContextVar[SecurityContext | None] = ContextVar(
    "security_context", default=None
)


@dataclass(frozen=True)
class SecurityContext:
    user: UserIdentity
    tenant: TenantIdentity
    roles: tuple[RoleSummary, ...] = field(default_factory=tuple)
    permissions: PermissionSummary = field(default_factory=PermissionSummary)
    data_scope: ResolvedDataScope = field(default_factory=ResolvedDataScope)

    @classmethod
    def current(cls) -> SecurityContext | None:
        return _security_context.get()

    @classmethod
    def set(cls, ctx: SecurityContext | None) -> object:
        return _security_context.set(ctx)

    @classmethod
    def reset(cls, token: object) -> None:
        _security_context.reset(token)

    def is_authorized(self, permission_code: str) -> bool:
        if self.user.is_platform_admin or self.user.is_tenant_admin:
            return True
        return self.permissions.has(permission_code)

    def is_data_scope_subset(self, requested: ResolvedDataScope) -> bool:
        return self.data_scope.is_subset(requested)

    def has_role(self, role_code: str) -> bool:
        return any(r.role_code == role_code for r in self.roles)