"""DataScope 聚合根 - 数据权限范围。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4


class ScopeType(str, Enum):
    PLATFORM = "platform"
    TENANT = "tenant"
    ENTERPRISE = "enterprise"
    ORGANIZATION = "organization"
    WAREHOUSE = "warehouse"
    DEPARTMENT = "department"
    SELF = "self"


class AccessMode(str, Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


@dataclass
class DataScopeAggregate:
    """数据权限范围聚合根。"""

    id: UUID = field(default_factory=uuid4)
    role_id: UUID = field(default_factory=uuid4)
    scope_type: ScopeType = ScopeType.TENANT
    access_mode: AccessMode = AccessMode.READ
    org_ids: set[UUID] = field(default_factory=set)
    warehouse_ids: set[UUID] = field(default_factory=set)

    def is_subset(self, other: DataScopeAggregate) -> bool:
        if self.scope_type == ScopeType.PLATFORM:
            return True
        if other.scope_type == ScopeType.PLATFORM:
            return False
        if self.scope_type != other.scope_type:
            return False
        if not self.org_ids.issubset(other.org_ids):
            return False
        if not self.warehouse_ids.issubset(other.warehouse_ids):
            return False
        return True

    def can_write(self) -> bool:
        return self.access_mode in (AccessMode.WRITE, AccessMode.ADMIN)