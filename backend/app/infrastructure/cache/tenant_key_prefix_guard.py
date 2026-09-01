"""TenantKeyPrefixGuard - Redis Key 租户前缀守卫。

强制所有 Redis Key 格式为 eitp:{tenant_id}:*，拒绝无租户前缀的业务键写入。
平台级键白名单除外（platform:config:* / platform:mdm:group_product:*）。
"""

from __future__ import annotations

import re
from uuid import UUID

from app.interfaces.middleware.error_handler import SECError, SECErrorCode


_PREFIX_PATTERN = re.compile(r"^eitp:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:.+$")

_PLATFORM_KEY_WHITELIST: list[str] = [
    "platform:config:*",
    "platform:mdm:group_product:*",
    "platform:health:*",
    "platform:scheduler:*",
]

_PLATFORM_KEY_PATTERNS = [re.compile(p.replace("*", ".*")) for p in _PLATFORM_KEY_WHITELIST]


class TenantKeyPrefixGuard:
    """Redis Key 租户前缀守卫 - 强制 eitp:{tenant_id}:* 格式。"""

    strict_mode: bool = True
    prefix_pattern: str = "eitp:{tenant_id}:*"

    @staticmethod
    def is_platform_key(key: str) -> bool:
        return any(p.match(key) for p in _PLATFORM_KEY_PATTERNS)

    @staticmethod
    def validate(key: str, tenant_id: UUID | str | None = None) -> str:
        if TenantKeyPrefixGuard.is_platform_key(key):
            return key
        if not _PREFIX_PATTERN.match(key):
            raise SECError(
                SECErrorCode.REDIS_KEY_PREFIX_MISSING,
                f"Redis key '{key}' violates tenant prefix pattern 'eitp:{{tenant_id}}:*'",
            )
        if tenant_id is not None:
            expected_prefix = f"eitp:{str(tenant_id)}:"
            if not key.startswith(expected_prefix):
                raise SECError(
                    SECErrorCode.REDIS_KEY_VIOLATION,
                    f"Redis key '{key}' does not match expected tenant prefix '{expected_prefix}'",
                )
        return key

    @staticmethod
    def build_key(tenant_id: UUID | str, namespace: str, identifier: str) -> str:
        key = f"eitp:{str(tenant_id)}:{namespace}:{identifier}"
        return TenantKeyPrefixGuard.validate(key, tenant_id)

    @staticmethod
    def scan_violations(keys: list[str]) -> list[str]:
        violations: list[str] = []
        for key in keys:
            if TenantKeyPrefixGuard.is_platform_key(key):
                continue
            if not _PREFIX_PATTERN.match(key):
                violations.append(key)
        return violations