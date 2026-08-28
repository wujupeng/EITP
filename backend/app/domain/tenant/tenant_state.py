"""租户状态与数据放置枚举。"""

from __future__ import annotations

from enum import Enum


class TenantStatus(Enum):
    """租户状态 - 状态机受控流转。"""

    PROVISIONING = "provisioning"
    ACTIVE = "active"
    DISABLED = "disabled"
    DEPROVISIONED = "deprovisioned"
    FAILED = "failed"


class DataPlacement(Enum):
    """数据放置模式。"""

    SHARED_DB = "shared_db"
    DEDICATED_DB = "dedicated_db"
    DEDICATED_INSTANCE = "dedicated_instance"


VALID_TRANSITIONS: dict[TenantStatus, set[TenantStatus]] = {
    TenantStatus.PROVISIONING: {TenantStatus.ACTIVE, TenantStatus.FAILED},
    TenantStatus.ACTIVE: {TenantStatus.DISABLED},
    TenantStatus.DISABLED: {TenantStatus.ACTIVE, TenantStatus.DEPROVISIONED},
    TenantStatus.DEPROVISIONED: set(),
    TenantStatus.FAILED: {TenantStatus.PROVISIONING},
}