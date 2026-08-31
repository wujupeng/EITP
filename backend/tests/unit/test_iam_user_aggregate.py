"""EITP-IAM-001 用户聚合根与账号状态机单元测试。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.domain.identity.aggregates.user_aggregate import AccountStatus, UserAggregate
from app.domain.identity.events.user_events import (
    UserActivatedEvent,
    UserDeactivatedEvent,
    UserDisabledEvent,
    UserLockedEvent,
    UserPasswordChangedEvent,
)
from app.domain.policy.aggregates.password_policy_aggregate import PasswordPolicyAggregate
from app.domain.policy.services.password_hasher import Argon2Hasher
from app.domain.policy.services.password_strength_validator import PasswordStrengthValidator
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import IAMError, IAMErrorCode

_OLD_PASSWORD = "OldPassw0rd!2024"
_NEW_PASSWORD = "BrandN3wP@ss!2024"


def _make_user(
    account_status: AccountStatus = AccountStatus.PENDING_ACTIVATION,
    password_hash: str = "hash",
    password_salt: str = "salt",
    username: str = "testuser",
    email: str = "testuser@example.com",
) -> UserAggregate:
    return UserAggregate(
        id=EntityId.generate(),
        tenant_id=uuid4(),
        username=username,
        password_hash=password_hash,
        password_salt=password_salt,
        email=email,
        account_status=account_status,
    )


@pytest.fixture
def hasher() -> Argon2Hasher:
    return Argon2Hasher()


@pytest.fixture
def validator() -> PasswordStrengthValidator:
    return PasswordStrengthValidator()


@pytest.fixture
def policy() -> PasswordPolicyAggregate:
    return PasswordPolicyAggregate()


@pytest.fixture
def user_with_password(hasher: Argon2Hasher) -> UserAggregate:
    result = hasher.hash(_OLD_PASSWORD)
    return _make_user(password_hash=result.hash, password_salt=result.salt)


class UserAggregateTest:
    def test_create_with_valid_parameters(self) -> None:
        uid = EntityId.generate()
        tenant_id = uuid4()
        user = UserAggregate(
            id=uid,
            tenant_id=tenant_id,
            username="alice",
            password_hash="hash",
            password_salt="salt",
            email="alice@example.com",
            phone="13800000000",
            real_name="Alice",
            is_platform_admin=False,
            is_tenant_admin=True,
        )
        assert user.id == uid
        assert user.tenant_id == tenant_id
        assert user.username == "alice"
        assert user.email == "alice@example.com"
        assert user.phone == "13800000000"
        assert user.real_name == "Alice"
        assert user.account_status == AccountStatus.PENDING_ACTIVATION
        assert user.failed_login_count == 0
        assert user.is_tenant_admin is True
        assert user.is_platform_admin is False

    def test_full_status_lifecycle(self) -> None:
        user = _make_user(AccountStatus.PENDING_ACTIVATION)
        user.activate()
        assert user.account_status == AccountStatus.ACTIVE
        user.lock(duration_minutes=15)
        assert user.account_status == AccountStatus.LOCKED
        assert user.locked_until is not None
        user.disable()
        assert user.account_status == AccountStatus.DISABLED
        user.deactivate(confirm_token="confirm-token")
        assert user.account_status == AccountStatus.DEACTIVATED

    def test_illegal_transition_pending_to_locked(self) -> None:
        user = _make_user(AccountStatus.PENDING_ACTIVATION)
        with pytest.raises(IAMError) as exc:
            user.lock(duration_minutes=15)
        assert exc.value.code == IAMErrorCode.ACCOUNT_LOCKED

    def test_illegal_transition_disabled_to_locked(self) -> None:
        user = _make_user(AccountStatus.DISABLED)
        with pytest.raises(IAMError) as exc:
            user.lock(duration_minutes=15)
        assert exc.value.code == IAMErrorCode.ACCOUNT_LOCKED

    def test_deactivated_is_terminal(self) -> None:
        user = _make_user(AccountStatus.DEACTIVATED)
        with pytest.raises(IAMError) as exc:
            user.activate()
        assert exc.value.code == IAMErrorCode.ACCOUNT_LOCKED

    def test_activate_records_event(self) -> None:
        user = _make_user(AccountStatus.PENDING_ACTIVATION)
        user.activate()
        events = list(user.pull_events())
        assert len(events) == 1
        assert isinstance(events[0], UserActivatedEvent)

    def test_lock_records_event(self) -> None:
        user = _make_user(AccountStatus.ACTIVE)
        user.lock(duration_minutes=30)
        events = list(user.pull_events())
        assert len(events) == 1
        assert isinstance(events[0], UserLockedEvent)
        assert events[0].duration_minutes == 30

    def test_disable_records_event(self) -> None:
        user = _make_user(AccountStatus.ACTIVE)
        user.disable()
        events = list(user.pull_events())
        assert isinstance(events[0], UserDisabledEvent)

    def test_deactivate_requires_confirm_token(self) -> None:
        user = _make_user(AccountStatus.ACTIVE)
        with pytest.raises(IAMError) as exc:
            user.deactivate()
        assert exc.value.code == IAMErrorCode.DEACTIVATE_CONFIRM_REQUIRED

    def test_deactivate_records_event(self) -> None:
        user = _make_user(AccountStatus.ACTIVE)
        user.deactivate(confirm_token="token")
        events = list(user.pull_events())
        assert isinstance(events[0], UserDeactivatedEvent)

    def test_enable_from_disabled(self) -> None:
        user = _make_user(AccountStatus.DISABLED)
        user.enable()
        assert user.account_status == AccountStatus.ACTIVE

    def test_unlock_resets_failed_count_and_locked_until(self) -> None:
        user = _make_user(AccountStatus.ACTIVE)
        for _ in range(4):
            user.increment_failed_count(max_attempts=5, lockout_minutes=15)
        locked = user.increment_failed_count(max_attempts=5, lockout_minutes=15)
        assert locked is True
        assert user.account_status == AccountStatus.LOCKED
        assert user.failed_login_count == 5
        user.unlock()
        assert user.account_status == AccountStatus.ACTIVE
        assert user.failed_login_count == 0
        assert user.locked_until is None

    def test_increment_failed_count_below_threshold(self) -> None:
        user = _make_user(AccountStatus.ACTIVE)
        locked = user.increment_failed_count(max_attempts=5, lockout_minutes=15)
        assert locked is False
        assert user.failed_login_count == 1
        assert user.account_status == AccountStatus.ACTIVE

    def test_reset_failed_count(self) -> None:
        user = _make_user(AccountStatus.ACTIVE)
        user.increment_failed_count(max_attempts=5, lockout_minutes=15)
        user.increment_failed_count(max_attempts=5, lockout_minutes=15)
        user.reset_failed_count()
        assert user.failed_login_count == 0

    def test_verify_password_correct(self, hasher: Argon2Hasher) -> None:
        result = hasher.hash("MySecret123!")
        user = _make_user(password_hash=result.hash, password_salt=result.salt)
        assert user.verify_password("MySecret123!", hasher) is True

    def test_verify_password_wrong(self, hasher: Argon2Hasher) -> None:
        result = hasher.hash("MySecret123!")
        user = _make_user(password_hash=result.hash, password_salt=result.salt)
        assert user.verify_password("WrongSecret!", hasher) is False

    def test_change_password_wrong_old_raises(
        self,
        hasher: Argon2Hasher,
        validator: PasswordStrengthValidator,
        policy: PasswordPolicyAggregate,
        user_with_password: UserAggregate,
    ) -> None:
        with pytest.raises(IAMError) as exc:
            user_with_password.change_password("WrongOld123!", _NEW_PASSWORD, hasher, validator, policy)
        assert exc.value.code == IAMErrorCode.OLD_PASSWORD_INVALID

    def test_change_password_weak_new_raises(
        self,
        hasher: Argon2Hasher,
        validator: PasswordStrengthValidator,
        policy: PasswordPolicyAggregate,
        user_with_password: UserAggregate,
    ) -> None:
        with pytest.raises(IAMError) as exc:
            user_with_password.change_password(_OLD_PASSWORD, "weak", hasher, validator, policy)
        assert exc.value.code == IAMErrorCode.PASSWORD_WEAK

    def test_change_password_reused_raises(
        self,
        hasher: Argon2Hasher,
        validator: PasswordStrengthValidator,
        policy: PasswordPolicyAggregate,
        user_with_password: UserAggregate,
    ) -> None:
        with pytest.raises(IAMError) as exc:
            user_with_password.change_password(
                _OLD_PASSWORD, _NEW_PASSWORD, hasher, validator, policy, is_reused=True
            )
        assert exc.value.code == IAMErrorCode.PASSWORD_REUSE_DENIED

    def test_password_history_reuse_prevention(
        self,
        hasher: Argon2Hasher,
        validator: PasswordStrengthValidator,
        policy: PasswordPolicyAggregate,
    ) -> None:
        result = hasher.hash(_OLD_PASSWORD)
        user = _make_user(password_hash=result.hash, password_salt=result.salt)
        history = ["Hist0ryP@ss!1", "Hist0ryP@ss!2", "Hist0ryP@ss!3"]
        for hist_pw in history:
            with pytest.raises(IAMError) as exc:
                user.change_password(_OLD_PASSWORD, hist_pw, hasher, validator, policy, is_reused=True)
            assert exc.value.code == IAMErrorCode.PASSWORD_REUSE_DENIED

    def test_change_password_success_updates_hash_and_expiry(
        self,
        hasher: Argon2Hasher,
        validator: PasswordStrengthValidator,
        policy: PasswordPolicyAggregate,
        user_with_password: UserAggregate,
    ) -> None:
        old_hash = user_with_password.password_hash
        user_with_password.change_password(_OLD_PASSWORD, _NEW_PASSWORD, hasher, validator, policy)
        assert user_with_password.password_hash != old_hash
        assert user_with_password.password_changed_at is not None
        assert user_with_password.password_expires_at is not None
        expected_expiry = user_with_password.password_changed_at + timedelta(days=policy.expire_days)
        assert user_with_password.password_expires_at == expected_expiry
        events = list(user_with_password.pull_events())
        assert isinstance(events[0], UserPasswordChangedEvent)
        assert hasher.verify(_NEW_PASSWORD, user_with_password.password_hash, user_with_password.password_salt)

    def test_password_not_expired_after_change(
        self,
        hasher: Argon2Hasher,
        validator: PasswordStrengthValidator,
        policy: PasswordPolicyAggregate,
        user_with_password: UserAggregate,
    ) -> None:
        user_with_password.change_password(_OLD_PASSWORD, _NEW_PASSWORD, hasher, validator, policy)
        assert user_with_password.is_password_expired(policy) is False

    def test_password_expired_when_past_expiry(self, policy: PasswordPolicyAggregate) -> None:
        past = datetime.now(timezone.utc) - timedelta(days=1)
        user = UserAggregate(
            id=EntityId.generate(),
            tenant_id=uuid4(),
            username="bob",
            password_hash="h",
            password_salt="s",
            password_expires_at=past,
        )
        assert user.is_password_expired(policy) is True

    def test_password_expired_none_returns_false(self, policy: PasswordPolicyAggregate) -> None:
        user = _make_user()
        assert user.is_password_expired(policy) is False

    def test_is_locked_when_locked_until_future(self) -> None:
        user = UserAggregate(
            id=EntityId.generate(),
            tenant_id=uuid4(),
            username="x",
            password_hash="h",
            password_salt="s",
            account_status=AccountStatus.LOCKED,
            locked_until=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        assert user.is_locked() is True

    def test_is_locked_auto_unlock_when_past(self) -> None:
        user = UserAggregate(
            id=EntityId.generate(),
            tenant_id=uuid4(),
            username="x",
            password_hash="h",
            password_salt="s",
            account_status=AccountStatus.LOCKED,
            locked_until=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        assert user.is_locked() is False

    def test_is_locked_false_when_not_locked_status(self) -> None:
        user = _make_user(AccountStatus.ACTIVE)
        assert user.is_locked() is False

    def test_record_login_updates_last_login(self) -> None:
        user = _make_user(AccountStatus.ACTIVE)
        assert user.last_login_at is None
        assert user.last_login_ip is None
        user.record_login("192.168.1.1")
        assert user.last_login_at is not None
        assert user.last_login_ip == "192.168.1.1"
        assert user.failed_login_count == 0

    def test_record_login_resets_failed_count(self) -> None:
        user = _make_user(AccountStatus.ACTIVE)
        user.increment_failed_count(max_attempts=5, lockout_minutes=15)
        user.increment_failed_count(max_attempts=5, lockout_minutes=15)
        assert user.failed_login_count == 2
        user.record_login("10.0.0.1")
        assert user.failed_login_count == 0