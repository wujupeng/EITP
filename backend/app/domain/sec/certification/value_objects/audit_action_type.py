"""AuditActionType 枚举 - 认证审计动作类型。"""

from __future__ import annotations

from enum import Enum


class AuditActionType(str, Enum):
    CERT_EXECUTE = "cert_execute"
    ITEM_PASS = "item_pass"
    ITEM_FAIL = "item_fail"
    ITEM_UNEXECUTABLE = "item_unexecutable"
    CERT_ISSUE = "cert_issue"
    CERT_REVOKE = "cert_revoke"
    CONFIG_CHANGE = "config_change"
    TAMPER_ATTEMPT = "tamper_attempt"
    PLATFORM_ADMIN_ACCESS = "platform_admin_access"
    REDIS_KEY_VIOLATION = "redis_key_violation"