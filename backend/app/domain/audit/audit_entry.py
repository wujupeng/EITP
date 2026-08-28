"""租户级审计日志 - 不可篡改，仅追加。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class AuditAction(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"
    REJECT = "reject"
    LOGIN = "login"
    LOGOUT = "logout"
    CONFIG_CHANGE = "config_change"
    DATASCOPE_VIOLATION = "datascope_violation"
    GROUP_READONLY_VIOLATION = "group_readonly_violation"
    MASTER_PROPAGATE = "master_propagate"


@dataclass(frozen=True)
class AuditEntry:
    """审计日志条目 - 不可篡改。

    每条记录包含：租户、操作人、动作、目标实体、前后值、时间戳。
    """

    id: UUID
    tenant_id: UUID
    user_id: UUID | None
    action: AuditAction
    entity_type: str
    entity_id: str
    old_value: dict | None
    new_value: dict | None
    ip_address: str | None
    occurred_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        user_id: UUID | None,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        old_value: dict | None = None,
        new_value: dict | None = None,
        ip_address: str | None = None,
    ) -> AuditEntry:
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            occurred_at=datetime.now(timezone.utc),
        )