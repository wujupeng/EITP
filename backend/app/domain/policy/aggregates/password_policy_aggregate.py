"""密码策略聚合根 - 封装密码策略规则与校验逻辑。

禁止贫血模型：所有密码策略行为内聚于聚合根中。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from app.interfaces.middleware.error_handler import IAMError, IAMErrorCode


class PolicyScope(str, Enum):
    PLATFORM = "platform"
    TENANT = "tenant"


@dataclass
class PasswordPolicyAggregate:
    """密码策略聚合根。"""

    id: UUID = field(default_factory=uuid4)
    scope_level: PolicyScope = PolicyScope.PLATFORM
    tenant_id: Optional[UUID] = None
    min_length: int = 12
    required_char_categories: int = 3
    history_count: int = 5
    expire_days: int = 90
    expire_grace_days: int = 30
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    ip_ban_threshold: int = 20
    ip_ban_duration_minutes: int = 60

    def validate(self, password: str, username: str = "", email: str = "") -> None:
        """校验密码是否符合策略。"""
        if len(password) < self.min_length:
            raise IAMError(
                IAMErrorCode.PASSWORD_WEAK,
                f"密码长度不足，最少需要 {self.min_length} 位",
            )

        categories = 0
        if any(c.islower() for c in password):
            categories += 1
        if any(c.isupper() for c in password):
            categories += 1
        if any(c.isdigit() for c in password):
            categories += 1
        if any(not c.isalnum() for c in password):
            categories += 1

        if categories < self.required_char_categories:
            raise IAMError(
                IAMErrorCode.PASSWORD_WEAK,
                f"密码字符类别不足，需要至少 {self.required_char_categories} 类（大写/小写/数字/特殊字符）",
            )

        if username and username.lower() in password.lower():
            raise IAMError(
                IAMErrorCode.PASSWORD_WEAK,
                "密码不得包含用户名",
            )

        if email and email.split("@")[0].lower() in password.lower():
            raise IAMError(
                IAMErrorCode.PASSWORD_WEAK,
                "密码不得包含邮箱前缀",
            )

    def merge_with_platform_redline(self, platform: PasswordPolicyAggregate) -> PasswordPolicyAggregate:
        """租户级策略与平台红线合并，强制不低于平台红线。"""
        if self.scope_level != PolicyScope.TENANT:
            raise IAMError(
                IAMErrorCode.PASSWORD_POLICY_BELOW_PLATFORM,
                "仅租户级策略可合并平台红线",
            )

        violations: list[str] = []
        if self.min_length < platform.min_length:
            violations.append(f"min_length({self.min_length}) < 平台红线({platform.min_length})")
        if self.required_char_categories < platform.required_char_categories:
            violations.append(f"required_char_categories({self.required_char_categories}) < 平台红线({platform.required_char_categories})")
        if self.history_count < platform.history_count:
            violations.append(f"history_count({self.history_count}) < 平台红线({platform.history_count})")
        if self.expire_days > platform.expire_days:
            violations.append(f"expire_days({self.expire_days}) > 平台红线({platform.expire_days})")
        if self.max_login_attempts > platform.max_login_attempts:
            violations.append(f"max_login_attempts({self.max_login_attempts}) > 平台红线({platform.max_login_attempts})")
        if self.lockout_duration_minutes < platform.lockout_duration_minutes:
            violations.append(f"lockout_duration_minutes({self.lockout_duration_minutes}) < 平台红线({platform.lockout_duration_minutes})")

        if violations:
            raise IAMError(
                IAMErrorCode.PASSWORD_POLICY_BELOW_PLATFORM,
                f"租户策略低于平台红线: {'; '.join(violations)}",
            )

        return self

    @classmethod
    def platform_default(cls) -> PasswordPolicyAggregate:
        """平台级默认红线策略。"""
        return cls(
            scope_level=PolicyScope.PLATFORM,
            min_length=12,
            required_char_categories=3,
            history_count=5,
            expire_days=90,
            expire_grace_days=30,
            max_login_attempts=5,
            lockout_duration_minutes=15,
            ip_ban_threshold=20,
            ip_ban_duration_minutes=60,
        )

    @classmethod
    def tenant_default(cls, tenant_id: UUID) -> PasswordPolicyAggregate:
        """租户级默认策略（与平台红线一致）。"""
        return cls(
            scope_level=PolicyScope.TENANT,
            tenant_id=tenant_id,
            min_length=12,
            required_char_categories=3,
            history_count=5,
            expire_days=90,
            expire_grace_days=30,
            max_login_attempts=5,
            lockout_duration_minutes=15,
            ip_ban_threshold=20,
            ip_ban_duration_minutes=60,
        )