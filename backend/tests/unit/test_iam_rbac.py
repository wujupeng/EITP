"""EITP-IAM-001 RBAC 角色-权限并集与 DataScope 交换单元测试。"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.authz.aggregates.data_scope_aggregate import (
    AccessMode,
    DataScopeAggregate,
    ScopeType,
)
from app.domain.authz.aggregates.role_aggregate import BuiltinRole, RoleAggregate
from app.domain.authz.entities.permission import BUILTIN_PERMISSIONS, Permission
from app.interfaces.middleware.error_handler import IAMError, IAMErrorCode


class PermissionTest:
    def test_create_permission(self) -> None:
        p = Permission.create(code="iam:user:read", name="查看用户", module="iam")
        assert p.code == "iam:user:read"
        assert p.name == "查看用户"
        assert p.module == "iam"

    def test_builtin_permissions_populated(self) -> None:
        codes = [entry["code"] for entry in BUILTIN_PERMISSIONS]
        assert "iam:user:read" in codes
        assert "iam:user:write" in codes
        assert "platform:tenant:write" in codes
        assert len(BUILTIN_PERMISSIONS) >= 10

    def test_builtin_permissions_all_have_required_fields(self) -> None:
        for entry in BUILTIN_PERMISSIONS:
            assert entry["code"]
            assert entry["name"]
            assert entry["module"]


class RoleAggregateTest:
    def test_default_values(self) -> None:
        role = RoleAggregate(role_code="custom", tenant_id=uuid4())
        assert role.is_builtin is False
        assert role.is_active is True
        assert role.permission_ids == set()

    def test_add_permission(self) -> None:
        role = RoleAggregate(role_code="custom", tenant_id=uuid4())
        pid = uuid4()
        role.add_permission(pid)
        assert pid in role.permission_ids

    def test_add_permission_is_idempotent(self) -> None:
        pid = uuid4()
        role = RoleAggregate(role_code="custom", tenant_id=uuid4())
        role.add_permission(pid)
        role.add_permission(pid)
        assert role.permission_ids == {pid}

    def test_remove_permission_custom_role(self) -> None:
        pid = uuid4()
        role = RoleAggregate(role_code="custom", tenant_id=uuid4(), permission_ids={pid})
        role.remove_permission(pid)
        assert pid not in role.permission_ids

    def test_remove_permission_builtin_raises(self) -> None:
        pid = uuid4()
        role = RoleAggregate.builtin(uuid4(), BuiltinRole.TENANT_ADMIN)
        role.add_permission(pid)
        with pytest.raises(IAMError) as exc:
            role.remove_permission(pid)
        assert exc.value.code == IAMErrorCode.BUILTIN_ROLE_PROTECTED

    def test_deactivate_builtin_raises(self) -> None:
        role = RoleAggregate.builtin(uuid4(), BuiltinRole.TENANT_ADMIN)
        with pytest.raises(IAMError) as exc:
            role.deactivate()
        assert exc.value.code == IAMErrorCode.BUILTIN_ROLE_PROTECTED

    def test_deactivate_and_activate_custom_role(self) -> None:
        role = RoleAggregate(role_code="custom", tenant_id=uuid4())
        role.deactivate()
        assert role.is_active is False
        role.activate()
        assert role.is_active is True

    def test_multi_role_permission_union(self) -> None:
        p1, p2, p3 = uuid4(), uuid4(), uuid4()
        role_a = RoleAggregate(role_code="a", tenant_id=uuid4(), permission_ids={p1, p2})
        role_b = RoleAggregate(role_code="b", tenant_id=uuid4(), permission_ids={p2, p3})
        role_c = RoleAggregate(role_code="c", tenant_id=uuid4(), permission_ids={p1})
        union = set().union(role_a.permission_ids, role_b.permission_ids, role_c.permission_ids)
        assert union == {p1, p2, p3}

    def test_multi_role_union_no_duplicates(self) -> None:
        p1, p2 = uuid4(), uuid4()
        role_a = RoleAggregate(role_code="a", tenant_id=uuid4(), permission_ids={p1, p2})
        role_b = RoleAggregate(role_code="b", tenant_id=uuid4(), permission_ids={p1, p2})
        union = role_a.permission_ids | role_b.permission_ids
        assert union == {p1, p2}

    def test_multi_role_empty_union(self) -> None:
        role_a = RoleAggregate(role_code="a", tenant_id=uuid4())
        role_b = RoleAggregate(role_code="b", tenant_id=uuid4())
        union = role_a.permission_ids | role_b.permission_ids
        assert union == set()

    def test_builtin_role_creation_for_all_enums(self) -> None:
        tid = uuid4()
        for role_enum in BuiltinRole:
            role = RoleAggregate.builtin(tid, role_enum)
            assert role.is_builtin is True
            assert role.role_code == role_enum.value
            assert role.role_name

    def test_builtin_role_names(self) -> None:
        tid = uuid4()
        assert RoleAggregate.builtin(tid, BuiltinRole.PLATFORM_SUPER_ADMIN).role_name == "平台超级管理员"
        assert RoleAggregate.builtin(tid, BuiltinRole.MULTI_TENANT_ADMIN).role_name == "多租户管理员"
        assert RoleAggregate.builtin(tid, BuiltinRole.TENANT_ADMIN).role_name == "租户管理员"
        assert RoleAggregate.builtin(tid, BuiltinRole.ENTERPRISE_ADMIN).role_name == "企业管理员"
        assert RoleAggregate.builtin(tid, BuiltinRole.BUSINESS_USER).role_name == "业务用户"


class DataScopeAggregateTest:
    def test_default_values(self) -> None:
        scope = DataScopeAggregate()
        assert scope.scope_type == ScopeType.TENANT
        assert scope.access_mode == AccessMode.READ
        assert scope.org_ids == set()
        assert scope.warehouse_ids == set()

    def test_can_write_for_read_only(self) -> None:
        scope = DataScopeAggregate(access_mode=AccessMode.READ)
        assert scope.can_write() is False

    def test_can_write_for_write(self) -> None:
        scope = DataScopeAggregate(access_mode=AccessMode.WRITE)
        assert scope.can_write() is True

    def test_can_write_for_admin(self) -> None:
        scope = DataScopeAggregate(access_mode=AccessMode.ADMIN)
        assert scope.can_write() is True

    def test_platform_scope_is_subset_of_anything(self) -> None:
        platform_scope = DataScopeAggregate(scope_type=ScopeType.PLATFORM)
        tenant_scope = DataScopeAggregate(scope_type=ScopeType.TENANT)
        assert platform_scope.is_subset(tenant_scope) is True

    def test_non_platform_not_subset_of_platform(self) -> None:
        tenant_scope = DataScopeAggregate(scope_type=ScopeType.TENANT)
        platform_scope = DataScopeAggregate(scope_type=ScopeType.PLATFORM)
        assert tenant_scope.is_subset(platform_scope) is False

    def test_same_scope_subset_with_org_ids(self) -> None:
        org_a = uuid4()
        org_b = uuid4()
        narrow = DataScopeAggregate(scope_type=ScopeType.ORGANIZATION, org_ids={org_a})
        wide = DataScopeAggregate(scope_type=ScopeType.ORGANIZATION, org_ids={org_a, org_b})
        assert narrow.is_subset(wide) is True
        assert wide.is_subset(narrow) is False

    def test_different_scope_types_not_subset(self) -> None:
        org_scope = DataScopeAggregate(scope_type=ScopeType.ORGANIZATION)
        dept_scope = DataScopeAggregate(scope_type=ScopeType.DEPARTMENT)
        assert org_scope.is_subset(dept_scope) is False
        assert dept_scope.is_subset(org_scope) is False

    def test_warehouse_ids_subset(self) -> None:
        w1, w2 = uuid4(), uuid4()
        narrow = DataScopeAggregate(scope_type=ScopeType.WAREHOUSE, warehouse_ids={w1})
        wide = DataScopeAggregate(scope_type=ScopeType.WAREHOUSE, warehouse_ids={w1, w2})
        assert narrow.is_subset(wide) is True
        assert wide.is_subset(narrow) is False

    def test_warehouse_ids_violation_not_subset(self) -> None:
        w1, w2 = uuid4(), uuid4()
        narrow = DataScopeAggregate(scope_type=ScopeType.WAREHOUSE, warehouse_ids={w1, w2})
        wide = DataScopeAggregate(scope_type=ScopeType.WAREHOUSE, warehouse_ids={w1})
        assert narrow.is_subset(wide) is False

    def test_privilege_escalation_prevented(self) -> None:
        org_a = uuid4()
        org_b = uuid4()
        org_c = uuid4()
        authorized = DataScopeAggregate(scope_type=ScopeType.ORGANIZATION, org_ids={org_a, org_b})
        narrower = DataScopeAggregate(scope_type=ScopeType.ORGANIZATION, org_ids={org_a})
        wider = DataScopeAggregate(scope_type=ScopeType.ORGANIZATION, org_ids={org_a, org_b, org_c})
        assert narrower.is_subset(authorized) is True
        assert wider.is_subset(authorized) is False

    def test_dynamic_semantic_resolution_narrows_by_org_set(self) -> None:
        orgs = [uuid4() for _ in range(5)]
        full = DataScopeAggregate(scope_type=ScopeType.ORGANIZATION, org_ids=set(orgs))
        resolved = DataScopeAggregate(scope_type=ScopeType.ORGANIZATION, org_ids={orgs[0], orgs[1]})
        assert resolved.is_subset(full) is True
        assert full.is_subset(resolved) is False

    def test_empty_org_ids_subset_of_any_same_scope(self) -> None:
        org_a = uuid4()
        empty = DataScopeAggregate(scope_type=ScopeType.ORGANIZATION, org_ids=set())
        wide = DataScopeAggregate(scope_type=ScopeType.ORGANIZATION, org_ids={org_a})
        assert empty.is_subset(wide) is True

    def test_scope_type_dimensions_exist(self) -> None:
        expected = {
            ScopeType.PLATFORM,
            ScopeType.TENANT,
            ScopeType.ENTERPRISE,
            ScopeType.ORGANIZATION,
            ScopeType.WAREHOUSE,
            ScopeType.DEPARTMENT,
            ScopeType.SELF,
        }
        assert set(ScopeType) == expected

    def test_access_mode_dimensions_exist(self) -> None:
        assert set(AccessMode) == {AccessMode.READ, AccessMode.WRITE, AccessMode.ADMIN}

    def test_self_scope_subset_of_same_self(self) -> None:
        org_a = uuid4()
        a = DataScopeAggregate(scope_type=ScopeType.SELF, org_ids={org_a})
        b = DataScopeAggregate(scope_type=ScopeType.SELF, org_ids={org_a})
        assert a.is_subset(b) is True