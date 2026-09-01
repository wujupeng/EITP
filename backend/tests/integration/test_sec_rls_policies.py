"""sec_* 表 RLS 策略集成测试。"""

from __future__ import annotations

import pytest

from app.domain.sec.certification.value_objects.isolation_layer import IsolationLayer


_RLS_TENANT_TABLES = [
    "sec_certification_audit",
    "sec_platform_admin_access_log",
]

_RLS_PLATFORM_EXEMPT_TABLES = [
    "sec_certification_batch",
    "sec_certification_item",
    "sec_certification_report",
    "sec_certification_certificate",
    "sec_certification_config",
    "sec_platform_admin_access_request",
    "sec_redis_key_violation",
]


class TestRLSPolicies:
    """RLS 策略集成测试。"""

    def test_tenant_isolated_tables_defined(self) -> None:
        assert len(_RLS_TENANT_TABLES) == 2
        assert "sec_certification_audit" in _RLS_TENANT_TABLES
        assert "sec_platform_admin_access_log" in _RLS_TENANT_TABLES

    def test_platform_exempt_tables_defined(self) -> None:
        assert len(_RLS_PLATFORM_EXEMPT_TABLES) == 7
        assert "sec_certification_batch" in _RLS_PLATFORM_EXEMPT_TABLES
        assert "sec_certification_config" in _RLS_PLATFORM_EXEMPT_TABLES

    def test_no_table_in_both_groups(self) -> None:
        overlap = set(_RLS_TENANT_TABLES) & set(_RLS_PLATFORM_EXEMPT_TABLES)
        assert len(overlap) == 0

    def test_all_sec_tables_covered(self) -> None:
        all_tables = set(_RLS_TENANT_TABLES) | set(_RLS_PLATFORM_EXEMPT_TABLES)
        expected = {
            "sec_certification_batch", "sec_certification_item", "sec_certification_report",
            "sec_certification_certificate", "sec_certification_config", "sec_certification_audit",
            "sec_platform_admin_access_request", "sec_platform_admin_access_log",
            "sec_redis_key_violation",
        }
        assert all_tables == expected

    def test_rls_policy_sql_contains_tenant_id(self) -> None:
        tenant_policy = "tenant_id = current_setting('app.current_tenant_id', true)::uuid"
        assert "tenant_id" in tenant_policy
        assert "current_setting" in tenant_policy

    def test_platform_exempt_policy_contains_or_condition(self) -> None:
        platform_policy = "OR current_setting('app.is_platform_admin', true) = 'true'"
        assert "OR" in platform_policy
        assert "is_platform_admin" in platform_policy