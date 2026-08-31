"""用户聚合根 - 账号状态机、密码校验、登录行为。

禁止贫血模型：所有用户行为内聚于聚合根中。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional
from uuid import UUID

from app.domain.identity.events.user_events import (
    UserActivatedEvent,
    UserDeactivatedEvent,
    UserDisabledEvent,
    UserLockedEvent,
    UserPasswordChangedEvent,
)
from app.domain.policy.aggregates.password_policy_aggregate import PasswordPolicyAggregate
from app.domain.policy.services.password_hasher import PasswordHashStrategy
from app.domain.policy.services.password_strength_validator import (
    PasswordStrengthValidator,
    ValidationResult,
)
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import IAMError, IAMErrorCode


class AccountStatus(str, Enum):
    PENDING_ACTIVATION = "pending_activation"
    ACTIVE = "active"
    LOCKED = "locked"
    DISABLED = "disabled"
    DEACTIVATED = "deactivated"


VALID_TRANSITIONS: dict[AccountStatus, set[AccountStatus]] = {
    AccountStatus.PENDING_ACTIVATION: {AccountStatus.ACTIVE, AccountStatus.DISABLED, AccountStatus.DEACTIVATED},
    AccountStatus.ACTIVE: {AccountStatus.LOCKED, AccountStatus.DISABLED, AccountStatus.DEACTIVATED},
    AccountStatus.LOCKED: {AccountStatus.ACTIVE, AccountStatus.DISABLED, AccountStatus.DEACTIVATED},
    AccountStatus.DISABLED: {AccountStatus.ACTIVE, AccountStatus.DEACTIVATED},
    AccountStatus.DEACTIVATED: set(),
}


class UserAggregate(AggregateRoot):
    """用户聚合根 - 管理账号生命周期、密码、登录状态。"""

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        username: str,
        password_hash: str,
        password_salt: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        real_name: Optional[str] = None,
        account_status: AccountStatus = AccountStatus.PENDING_ACTIVATION,
        failed_login_count: int = 0,
        locked_until: Optional[datetime] = None,
        password_changed_at: Optional[datetime] = None,
        password_expires_at: Optional[datetime] = None,
        last_login_at: Optional[datetime] = None,
        last_login_ip: Optional[str] = None,
        is_platform_admin: bool = False,
        is_tenant_admin: bool = False,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._username = username
        self._password_hash = password_hash
        self._password_salt = password_salt
        self._email = email
        self._phone = phone
        self._real_name = real_name
        self._account_status = account_status
        self._failed_login_count = failed_login_count
        self._locked_until = locked_until
        self._password_changed_at = password_changed_at
        self._password_expires_at = password_expires_at
        self._last_login_at = last_login_at
        self._last_login_ip = last_login_ip
        self._is_platform_admin = is_platform_admin
        self._is_tenant_admin = is_tenant_admin

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def username(self) -> str:
        return self._username

    @property
    def email(self) -> Optional[str]:
        return self._email

    @property
    def phone(self) -> Optional[str]:
        return self._phone

    @property
    def real_name(self) -> Optional[str]:
        return self._real_name

    @property
    def account_status(self) -> AccountStatus:
        return self._account_status

    @property
    def password_hash(self) -> str:
        return self._password_hash

    @property
    def password_salt(self) -> str:
        return self._password_salt

    @property
    def failed_login_count(self) -> int:
        return self._failed_login_count

    @property
    def locked_until(self) -> Optional[datetime]:
        return self._locked_until

    @property
    def password_changed_at(self) -> Optional[datetime]:
        return self._password_changed_at

    @property
    def password_expires_at(self) -> Optional[datetime]:
        return self._password_expires_at

    @property
    def last_login_at(self) -> Optional[datetime]:
        return self._last_login_at

    @property
    def last_login_ip(self) -> Optional[str]:
        return self._last_login_ip

    @property
    def is_platform_admin(self) -> bool:
        return self._is_platform_admin

    @property
    def is_tenant_admin(self) -> bool:
        return self._is_tenant_admin

    def _transition_to(self, new_status: AccountStatus) -> None:
        if new_status not in VALID_TRANSITIONS.get(self._account_status, set()):
            raise IAMError(
                IAMErrorCode.ACCOUNT_LOCKED,
                f"非法状态流转: {self._account_status.value} → {new_status.value}",
            )
        self._account_status = new_status
        self._touch()

    def activate(self) -> None:
        self._transition_to(AccountStatus.ACTIVE)
        self._record_event(
            UserActivatedEvent(user_id=self._id.value, tenant_id=self._tenant_id)
        )

    def lock(self, duration_minutes: int) -> None:
        self._transition_to(AccountStatus.LOCKED)
        self._locked_until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        self._touch()
        self._record_event(
            UserLockedEvent(
                user_id=self._id.value,
                tenant_id=self._tenant_id,
                duration_minutes=duration_minutes,
            )
        )

    def unlock(self) -> None:
        self._transition_to(AccountStatus.ACTIVE)
        self._locked_until = None
        self._failed_login_count = 0
        self._touch()

    def disable(self) -> None:
        self._transition_to(AccountStatus.DISABLED)
        self._touch()
        self._record_event(
            UserDisabledEvent(user_id=self._id.value, tenant_id=self._tenant_id)
        )

    def enable(self) -> None:
        self._transition_to(AccountStatus.ACTIVE)
        self._touch()

    def deactivate(self, confirm_token: Optional[str] = None) -> None:
        if confirm_token is None:
            raise IAMError(
                IAMErrorCode.DEACTIVATE_CONFIRM_REQUIRED,
                "注销用户需要二次确认令牌",
            )
        self._transition_to(AccountStatus.DEACTIVATED)
        self._touch()
        self._record_event(
            UserDeactivatedEvent(user_id=self._id.value, tenant_id=self._tenant_id)
        )

    def verify_password(self, plain: str, hasher: PasswordHashStrategy) -> bool:
        return hasher.verify(plain, self._password_hash, self._password_salt)

    def change_password(
        self,
        old: str,
        new: str,
        hasher: PasswordHashStrategy,
        validator: PasswordStrengthValidator,
        policy: PasswordPolicyAggregate,
        is_reused: bool = False,
    ) -> None:
        if not self.verify_password(old, hasher):
            raise IAMError(
                IAMErrorCode.OLD_PASSWORD_INVALID,
                "旧密码不正确",
            )

        result: ValidationResult = validator.validate(
            password=new,
            min_length=policy.min_length,
            required_categories=policy.required_char_categories,
            username=self._username,
            email=self._email or "",
        )
        if not result:
            raise IAMError(
                IAMErrorCode.PASSWORD_WEAK,
                f"密码强度不足: {'; '.join(result.violations)}",
            )

        if is_reused:
            raise IAMError(
                IAMErrorCode.PASSWORD_REUSE_DENIED,
                "新密码与历史密码重复",
            )

        hash_result = hasher.hash(new)
        self._password_hash = hash_result.hash
        self._password_salt = hash_result.salt
        now = datetime.now(timezone.utc)
        self._password_changed_at = now
        self._password_expires_at = now + timedelta(days=policy.expire_days)
        self._touch()
        self._record_event(
            UserPasswordChangedEvent(user_id=self._id.value, tenant_id=self._tenant_id)
        )

    def reset_failed_count(self) -> None:
        self._failed_login_count = 0
        self._touch()

    def increment_failed_count(self, max_attempts: int, lockout_minutes: int) -> bool:
        self._failed_login_count += 1
        if self._failed_login_count >= max_attempts:
            self.lock(lockout_minutes)
            return True
        self._touch()
        return False

    def is_password_expired(self, policy: PasswordPolicyAggregate) -> bool:
        if self._password_expires_at is None:
            return False
        return datetime.now(timezone.utc) > self._password_expires_at

    def is_locked(self) -> bool:
        if self._account_status != AccountStatus.LOCKED:
            return False
        if self._locked_until is not None:
            if datetime.now(timezone.utc) > self._locked_until:
                return False
        return True

    def record_login(self, ip_address: str) -> None:
        self._last_login_at = datetime.now(timezone.utc)
        self._last_login_ip = ip_address
        self._failed_login_count = 0
        self._touch()