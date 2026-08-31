"""EITP-IAM-001 密码策略与密码强度校验器单元测试。"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.policy.aggregates.password_policy_aggregate import (
    PasswordPolicyAggregate,
    PolicyScope,
)
from app.domain.policy.services.password_hasher import Argon2Hasher, BcryptHasher
from app.domain.policy.services.password_strength_validator import (
    PasswordStrengthValidator,
    ValidationResult,
)
from app.interfaces.middleware.error_handler import IAMError, IAMErrorCode


class Argon2HasherTest:
    def test_hash_differs_from_plaintext(self) -> None:
        hasher = Argon2Hasher()
        result = hasher.hash("S3cretPass!2024")
        assert result.hash != "S3cretPass!2024"
        assert "$argon2" in result.hash

    def test_different_salts_for_same_password(self) -> None:
        hasher = Argon2Hasher()
        r1 = hasher.hash("SamePassword123!")
        r2 = hasher.hash("SamePassword123!")
        assert r1.salt != r2.salt
        assert r1.hash != r2.hash

    def test_verify_correct_password(self) -> None:
        hasher = Argon2Hasher()
        result = hasher.hash("CorrectPass!123")
        assert hasher.verify("CorrectPass!123", result.hash, result.salt) is True

    def test_verify_wrong_password(self) -> None:
        hasher = Argon2Hasher()
        result = hasher.hash("CorrectPass!123")
        assert hasher.verify("WrongPass!999", result.hash, result.salt) is False

    def test_verify_corrupt_hash_returns_false(self) -> None:
        hasher = Argon2Hasher()
        assert hasher.verify("any", "corrupt-hash", "salt") is False


class BcryptHasherTest:
    def test_bcrypt_hash_and_verify(self) -> None:
        hasher = BcryptHasher()
        result = hasher.hash("BcryptPass!123")
        assert result.hash != "BcryptPass!123"
        assert hasher.verify("BcryptPass!123", result.hash, result.salt) is True
        assert hasher.verify("WrongPass!999", result.hash, result.salt) is False


class PasswordStrengthValidatorTest:
    @pytest.fixture
    def validator(self) -> PasswordStrengthValidator:
        return PasswordStrengthValidator()

    def test_strong_password_passes(self, validator: PasswordStrengthValidator) -> None:
        result = validator.validate("Str0ngP@ssword!2024", min_length=12, required_categories=3)
        assert result.is_valid is True
        assert result.violations == []

    def test_too_short_fails(self, validator: PasswordStrengthValidator) -> None:
        result = validator.validate("Short1!", min_length=12, required_categories=3)
        assert result.is_valid is False
        assert any("长度" in v for v in result.violations)

    def test_missing_categories_fails(self, validator: PasswordStrengthValidator) -> None:
        result = validator.validate("alllowercaseonly", min_length=12, required_categories=3)
        assert result.is_valid is False
        assert any("字符类别" in v for v in result.violations)

    def test_four_character_classes_pass(self, validator: PasswordStrengthValidator) -> None:
        result = validator.validate("Abcd1234!@#$", min_length=12, required_categories=4)
        assert result.is_valid is True

    def test_three_classes_when_four_required_fails(
        self, validator: PasswordStrengthValidator
    ) -> None:
        result = validator.validate("Abcd1234abcd", min_length=12, required_categories=4)
        assert result.is_valid is False

    def test_password_contains_username_fails(self, validator: PasswordStrengthValidator) -> None:
        result = validator.validate(
            "aliceUser123!alice", min_length=12, required_categories=3, username="alice"
        )
        assert result.is_valid is False
        assert any("用户名" in v for v in result.violations)

    def test_password_contains_email_prefix_fails(
        self, validator: PasswordStrengthValidator
    ) -> None:
        result = validator.validate(
            "alice123456!alice", min_length=12, required_categories=3, email="alice@example.com"
        )
        assert result.is_valid is False
        assert any("邮箱" in v for v in result.violations)

    def test_short_username_not_checked(self, validator: PasswordStrengthValidator) -> None:
        result = validator.validate(
            "ab12345678!ab", min_length=12, required_categories=3, username="ab"
        )
        assert "密码不得包含用户名" not in result.violations

    def test_validation_result_bool(self) -> None:
        ok = ValidationResult(is_valid=True)
        bad = ValidationResult(is_valid=False)
        assert bool(ok) is True
        assert bool(bad) is False


class PasswordPolicyAggregateTest:
    def test_default_values(self) -> None:
        p = PasswordPolicyAggregate()
        assert p.min_length == 12
        assert p.required_char_categories == 3
        assert p.history_count == 5
        assert p.expire_days == 90
        assert p.max_login_attempts == 5
        assert p.lockout_duration_minutes == 15
        assert p.ip_ban_threshold == 20

    def test_platform_default(self) -> None:
        p = PasswordPolicyAggregate.platform_default()
        assert p.scope_level == PolicyScope.PLATFORM
        assert p.min_length == 12
        assert p.required_char_categories == 3

    def test_tenant_default(self) -> None:
        tid = uuid4()
        p = PasswordPolicyAggregate.tenant_default(tid)
        assert p.scope_level == PolicyScope.TENANT
        assert p.tenant_id == tid
        assert p.min_length == 12

    def test_validate_strong_password_passes(self) -> None:
        p = PasswordPolicyAggregate()
        p.validate("Str0ngP@ss!2024", username="alice", email="alice@example.com")

    def test_validate_short_password_raises(self) -> None:
        p = PasswordPolicyAggregate()
        with pytest.raises(IAMError) as exc:
            p.validate("Short1!")
        assert exc.value.code == IAMErrorCode.PASSWORD_WEAK

    def test_validate_weak_categories_raises(self) -> None:
        p = PasswordPolicyAggregate()
        with pytest.raises(IAMError) as exc:
            p.validate("alllowercaseonly")
        assert exc.value.code == IAMErrorCode.PASSWORD_WEAK

    def test_validate_password_with_username_raises(self) -> None:
        p = PasswordPolicyAggregate()
        with pytest.raises(IAMError) as exc:
            p.validate("aliceUser123!alice", username="alice")
        assert exc.value.code == IAMErrorCode.PASSWORD_WEAK

    def test_validate_password_with_email_prefix_raises(self) -> None:
        p = PasswordPolicyAggregate()
        with pytest.raises(IAMError) as exc:
            p.validate("alice123456!alice", email="alice@example.com")
        assert exc.value.code == IAMErrorCode.PASSWORD_WEAK

    def test_history_count_configurable(self) -> None:
        p = PasswordPolicyAggregate(history_count=10)
        assert p.history_count == 10

    def test_tenant_policy_meeting_platform_redline_ok(self) -> None:
        platform = PasswordPolicyAggregate.platform_default()
        tenant = PasswordPolicyAggregate.tenant_default(uuid4())
        result = tenant.merge_with_platform_redline(platform)
        assert result is tenant

    def test_tenant_policy_min_length_below_platform_raises(self) -> None:
        platform = PasswordPolicyAggregate.platform_default()
        tenant = PasswordPolicyAggregate(scope_level=PolicyScope.TENANT, tenant_id=uuid4(), min_length=8)
        with pytest.raises(IAMError) as exc:
            tenant.merge_with_platform_redline(platform)
        assert exc.value.code == IAMErrorCode.PASSWORD_POLICY_BELOW_PLATFORM

    def test_tenant_policy_categories_below_platform_raises(self) -> None:
        platform = PasswordPolicyAggregate.platform_default()
        tenant = PasswordPolicyAggregate(
            scope_level=PolicyScope.TENANT, tenant_id=uuid4(), required_char_categories=2
        )
        with pytest.raises(IAMError) as exc:
            tenant.merge_with_platform_redline(platform)
        assert exc.value.code == IAMErrorCode.PASSWORD_POLICY_BELOW_PLATFORM

    def test_tenant_policy_history_below_platform_raises(self) -> None:
        platform = PasswordPolicyAggregate.platform_default()
        tenant = PasswordPolicyAggregate(scope_level=PolicyScope.TENANT, tenant_id=uuid4(), history_count=3)
        with pytest.raises(IAMError) as exc:
            tenant.merge_with_platform_redline(platform)
        assert exc.value.code == IAMErrorCode.PASSWORD_POLICY_BELOW_PLATFORM

    def test_tenant_expire_days_above_platform_raises(self) -> None:
        platform = PasswordPolicyAggregate.platform_default()
        tenant = PasswordPolicyAggregate(scope_level=PolicyScope.TENANT, tenant_id=uuid4(), expire_days=120)
        with pytest.raises(IAMError) as exc:
            tenant.merge_with_platform_redline(platform)
        assert exc.value.code == IAMErrorCode.PASSWORD_POLICY_BELOW_PLATFORM

    def test_tenant_max_login_attempts_above_platform_raises(self) -> None:
        platform = PasswordPolicyAggregate.platform_default()
        tenant = PasswordPolicyAggregate(
            scope_level=PolicyScope.TENANT, tenant_id=uuid4(), max_login_attempts=10
        )
        with pytest.raises(IAMError) as exc:
            tenant.merge_with_platform_redline(platform)
        assert exc.value.code == IAMErrorCode.PASSWORD_POLICY_BELOW_PLATFORM

    def test_tenant_lockout_below_platform_raises(self) -> None:
        platform = PasswordPolicyAggregate.platform_default()
        tenant = PasswordPolicyAggregate(
            scope_level=PolicyScope.TENANT, tenant_id=uuid4(), lockout_duration_minutes=5
        )
        with pytest.raises(IAMError) as exc:
            tenant.merge_with_platform_redline(platform)
        assert exc.value.code == IAMErrorCode.PASSWORD_POLICY_BELOW_PLATFORM

    def test_merge_non_tenant_raises(self) -> None:
        platform = PasswordPolicyAggregate.platform_default()
        other_platform = PasswordPolicyAggregate.platform_default()
        with pytest.raises(IAMError) as exc:
            other_platform.merge_with_platform_redline(platform)
        assert exc.value.code == IAMErrorCode.PASSWORD_POLICY_BELOW_PLATFORM