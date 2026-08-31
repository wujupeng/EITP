"""登录审计聚合根。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class LoginAction(str, Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    REFRESH = "refresh"
    PASSWORD_CHANGE = "password_change"
    ACCOUNT_LOCKED = "account_locked"
    IP_BANNED = "ip_banned"


@dataclass
class LoginAuditEntry:
    """登录审计记录。"""

    id: UUID = field(default_factory=uuid4)
    tenant_id: UUID | None = None
    user_id: UUID | None = None
    username: str = ""
    action: LoginAction = LoginAction.LOGIN
    success: bool = True
    ip_address: str = ""
    user_agent: str = ""
    failure_reason: str = ""
    trace_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))