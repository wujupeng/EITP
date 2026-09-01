"""EITP-SEC-001 TenantKeyPrefixGuard 单元测试。

覆盖 eitp:{tenant_id}:* 前缀强制、非合规键拒绝、平台白名单放行、build_key 与 scan_violations。
"""

from __future__ import annotations

from uuid import UUID

import pytest

from app.infrastructure.cache.tenant_key_prefix_guard import TenantKeyPrefixGuard
from app.interfaces.middleware.error_handler import SECError, SECErrorCode

_TENANT_A = UUID("11111111-1111-1111-1111-111111111111")
_TENANT_B = UUID("22222222-2222-2222-2222-222222222222")


class TenantKeyPrefixGuardTest:
    """TenantKeyPrefixGuard 前缀守卫。"""

    def test_validate_accepts_compliant_tenant_key(self) -> None:
        key = f"eitp:{_TENANT_A}:inv:product:1"
        assert TenantKeyPrefixGuard.validate(key, _TENANT_A) == key

    def test_validate_accepts_compliant_key_without_tenant_check(self) -> None:
        key = f"eitp:{_TENANT_A}:inv:product:1"
        assert TenantKeyPrefixGuard.validate(key) == key

    def test_validate_rejects_key_without_tenant_prefix(self) -> None:
        with pytest.raises(SECError) as exc:
            TenantKeyPrefixGuard.validate("bare_key")
        assert exc.value.code == SECErrorCode.REDIS_KEY_PREFIX_MISSING

    def test_validate_rejects_key_with_invalid_uuid_format(self) -> None:
        # eitp:not-a-uuid:x 不匹配 UUID 正则
        with pytest.raises(SECError) as exc:
            TenantKeyPrefixGuard.validate("eitp:not-a-uuid:inv:1")
        assert exc.value.code == SECErrorCode.REDIS_KEY_PREFIX_MISSING

    def test_validate_rejects_key_with_wrong_tenant_id(self) -> None:
        key = f"eitp:{_TENANT_B}:inv:product:1"
        with pytest.raises(SECError) as exc:
            TenantKeyPrefixGuard.validate(key, _TENANT_A)
        assert exc.value.code == SECErrorCode.REDIS_KEY_VIOLATION
        assert str(_TENANT_A) in exc.value.message

    def test_validate_rejects_key_missing_trailing_segment(self) -> None:
        # eitp:{uuid}: 后无内容，正则要求 .+ → 不匹配
        with pytest.raises(SECError) as exc:
            TenantKeyPrefixGuard.validate(f"eitp:{_TENANT_A}:")
        assert exc.value.code == SECErrorCode.REDIS_KEY_PREFIX_MISSING

    def test_is_platform_key_true_for_whitelist_patterns(self) -> None:
        assert TenantKeyPrefixGuard.is_platform_key("platform:config:global") is True
        assert TenantKeyPrefixGuard.is_platform_key("platform:mdm:group_product:1") is True
        assert TenantKeyPrefixGuard.is_platform_key("platform:health:live") is True
        assert TenantKeyPrefixGuard.is_platform_key("platform:scheduler:jobs") is True

    def test_is_platform_key_false_for_business_key(self) -> None:
        assert TenantKeyPrefixGuard.is_platform_key(f"eitp:{_TENANT_A}:inv:1") is False
        assert TenantKeyPrefixGuard.is_platform_key("random:key") is False

    def test_validate_allows_platform_whitelist_key_without_tenant(self) -> None:
        # 平台键跳过前缀校验，即便 tenant_id 不匹配
        assert TenantKeyPrefixGuard.validate("platform:config:global", _TENANT_A) == "platform:config:global"

    def test_build_key_constructs_compliant_key(self) -> None:
        key = TenantKeyPrefixGuard.build_key(_TENANT_A, "inv:product", "1")
        assert key == f"eitp:{_TENANT_A}:inv:product:1"

    def test_build_key_with_string_tenant_id(self) -> None:
        key = TenantKeyPrefixGuard.build_key(str(_TENANT_A), "wms:location", "LOC-1")
        assert key.startswith(f"eitp:{_TENANT_A}:wms:location:LOC-1")

    def test_scan_violations_returns_non_compliant_keys(self) -> None:
        keys = [
            f"eitp:{_TENANT_A}:inv:1",   # 合规
            "bare_key",                    # 违规
            "eitp:bad-uuid:x",             # 违规
            "platform:config:x",           # 白名单，跳过
        ]
        violations = TenantKeyPrefixGuard.scan_violations(keys)
        assert "bare_key" in violations
        assert "eitp:bad-uuid:x" in violations
        assert f"eitp:{_TENANT_A}:inv:1" not in violations
        assert "platform:config:x" not in violations

    def test_scan_violations_empty_for_all_compliant(self) -> None:
        keys = [f"eitp:{_TENANT_A}:inv:{i}" for i in range(5)]
        assert TenantKeyPrefixGuard.scan_violations(keys) == []

    def test_scan_violations_empty_for_all_platform_keys(self) -> None:
        keys = ["platform:config:a", "platform:health:b", "platform:scheduler:c"]
        assert TenantKeyPrefixGuard.scan_violations(keys) == []

    def test_strict_mode_and_prefix_pattern_constants(self) -> None:
        assert TenantKeyPrefixGuard.strict_mode is True
        assert TenantKeyPrefixGuard.prefix_pattern == "eitp:{tenant_id}:*"

    def test_validate_accepts_str_tenant_id(self) -> None:
        key = f"eitp:{_TENANT_A}:inv:1"
        assert TenantKeyPrefixGuard.validate(key, str(_TENANT_A)) == key