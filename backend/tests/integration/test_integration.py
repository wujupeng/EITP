"""T12 集成测试 - 跨模块调用与隔离穿透。

T12-06: 租户隔离穿透集成测试（C-SEC-01 四层纵深隔离）。
T12-09: 跨公司汇总与集团只读集成测试。
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.db import session as session_mod
from app.interfaces.middleware import tenant_context as tc_mod
from app.interfaces.middleware.tenant_context import TenantContext
from app.main import create_app


class _MockResult:
    def scalar_one_or_none(self):
        return None

    def scalars(self):
        return self

    def __iter__(self):
        return iter([])


class _MockSession:
    async def execute(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        return _MockResult()

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass


async def _mock_get_db_session():
    yield _MockSession()  # type: ignore[misc]


def _make_client_with_tenant(tenant_id=None, is_platform_admin=False) -> tuple[TestClient, str]:
    tc_mod.clear_token_cache()
    token = str(uuid4())
    ctx = TenantContext(
        tenant_id=tenant_id or uuid4(),
        is_platform_admin=is_platform_admin,
    )
    tc_mod._cache_set(token, ctx)
    app = create_app()
    app.dependency_overrides[session_mod.get_db_session] = _mock_get_db_session
    client = TestClient(app, raise_server_exceptions=False)
    return client, token


class TestTenantIsolationPenetration:
    """T12-06: 四层纵深隔离穿透测试（C-SEC-01）。"""

    def test_no_token_rejected(self) -> None:
        """无令牌访问业务接口被拒绝。"""
        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/v1/tenant/hierarchy/tree")
        assert response.status_code == 401

    def test_invalid_token_rejected(self) -> None:
        """非法令牌被拒绝。"""
        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(
            "/api/v1/tenant/hierarchy/tree",
            headers={"X-Tenant-Token": "invalid-token"},
        )
        assert response.status_code == 401

    def test_disabled_tenant_rejected(self) -> None:
        """停用租户业务接口被拒绝。"""
        tc_mod.clear_token_cache()
        token = str(uuid4())
        ctx = TenantContext(tenant_id=uuid4(), tenant_status="disabled")
        tc_mod._cache_set(token, ctx)
        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(
            "/api/v1/tenant/hierarchy/tree",
            headers={"X-Tenant-Token": token},
        )
        assert response.status_code == 403

    def test_different_tenants_isolated(self) -> None:
        """不同租户令牌互不可见。"""
        tenant_a = uuid4()
        tenant_b = uuid4()
        client_a, token_a = _make_client_with_tenant(tenant_a)
        client_b, token_b = _make_client_with_tenant(tenant_b)
        assert token_a != token_b
        assert tenant_a != tenant_b


class TestGroupReadonlyIntegration:
    """T12-09: 集团只读边界集成测试。"""

    def test_group_admin_write_rejected(self) -> None:
        """集团管理员写操作被拒绝。"""
        client, token = _make_client_with_tenant()
        enterprise = uuid4()

        response = client.post(
            f"/api/v1/group/readonly-check?enterprise_id={enterprise}",
            json={
                "is_group_admin": True,
                "operation": "create",
                "target_organization_id": str(uuid4()),
            },
            headers={"X-Tenant-Token": token},
        )
        assert response.status_code == 403
        assert "EITP_MT_GROUP_READONLY_VIOLATION" in response.text

    def test_group_admin_read_allowed(self) -> None:
        """集团管理员读操作允许。"""
        client, token = _make_client_with_tenant()
        enterprise = uuid4()

        response = client.post(
            f"/api/v1/group/readonly-check?enterprise_id={enterprise}",
            json={
                "is_group_admin": True,
                "operation": "read",
                "target_organization_id": str(uuid4()),
            },
            headers={"X-Tenant-Token": token},
        )
        assert response.status_code == 200

    def test_group_report_returns_delayed_flag(self) -> None:
        """集团报表返回 is_delayed 标记。"""
        client, token = _make_client_with_tenant()
        enterprise = uuid4()

        response = client.get(
            f"/api/v1/group/reports/sales?enterprise_id={enterprise}",
            headers={"X-Tenant-Token": token},
        )
        assert response.status_code == 200
        assert "is_delayed" in response.json()


class TestMasterDataPermissionIntegration:
    """T12: 主数据权限边界集成测试。"""

    def test_subsidiary_admin_cannot_modify_base(self) -> None:
        """子公司管理员修改集团基准被拒绝。"""
        client, token = _make_client_with_tenant()
        sku_id = uuid4()

        response = client.put(
            f"/api/v1/master-data/sku/{sku_id}",
            json={
                "base_attrs": {"name": "改"},
                "is_group_admin": False,
            },
            headers={"X-Tenant-Token": token},
        )
        assert response.status_code == 422
        assert "EITP_MT_MASTER_BASE_READONLY" in response.text


class TestBackupRestoreIntegration:
    """T12: 备份恢复集成测试。"""

    def test_cross_tenant_restore_denied(self) -> None:
        """跨租户恢复被拒绝（C-BACKUP-01）。"""
        client, token = _make_client_with_tenant()
        tenant_a = uuid4()
        tenant_b = uuid4()

        trigger = client.post(
            f"/api/v1/platform/backup/{tenant_a}",
            headers={"X-Tenant-Token": token},
        )
        backup_id = trigger.json()["backup_id"]

        response = client.post(
            f"/api/v1/platform/backup/{backup_id}/restore",
            json={"target_tenant_id": str(tenant_b)},
            headers={"X-Tenant-Token": token},
        )
        assert response.status_code == 403
        assert "EITP_MT_CROSS_TENANT_RESTORE_DENIED" in response.text


class TestPlacementMigrationIntegration:
    """T12: 放置与迁移集成测试。"""

    def test_placement_switch(self) -> None:
        """放置模式可切换。"""
        client, token = _make_client_with_tenant()
        tenant = uuid4()

        for mode in ["shared_db", "dedicated_db", "dedicated_instance"]:
            response = client.put(
                f"/api/v1/platform/placement/{tenant}",
                json={"placement": mode},
                headers={"X-Tenant-Token": token},
            )
            assert response.status_code == 200
            assert response.json()["placement"] == mode

    def test_migration_task_created(self) -> None:
        """迁移任务可创建并查询状态。"""
        client, token = _make_client_with_tenant()
        tenant = uuid4()

        migrate_resp = client.post(
            f"/api/v1/platform/placement/{tenant}/migrate",
            json={
                "target_placement": "dedicated_db",
                "maintenance_window": "2026-01-01T02:00:00/2026-01-01T04:00:00",
            },
            headers={"X-Tenant-Token": token},
        )
        assert migrate_resp.status_code == 202
        task_id = migrate_resp.json()["migration_task_id"]

        status_resp = client.get(
            f"/api/v1/platform/placement/{tenant}/migrate/{task_id}/status",
            headers={"X-Tenant-Token": token},
        )
        assert status_resp.status_code == 200