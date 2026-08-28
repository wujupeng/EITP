"""T07 集团报表 API 集成测试。"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.infrastructure.db import session as session_mod
from app.interfaces.middleware import tenant_context as tc_mod
from app.interfaces.middleware.tenant_context import TenantContext
from app.main import create_app


class _MockResult:
    """模拟查询结果 - 返回空列表。"""

    def scalar_one_or_none(self):
        return None

    def scalars(self):
        return self

    def __iter__(self):
        return iter([])


class _MockSession:
    """模拟异步数据库会话 - 不连接真实数据库。"""

    async def execute(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        return _MockResult()

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass


async def _mock_get_db_session():
    yield _MockSession()  # type: ignore[misc]


def _setup_app_with_mock_db() -> tuple[TestClient, str]:
    tc_mod.clear_token_cache()
    token = str(uuid4())
    ctx = TenantContext(tenant_id=uuid4())
    tc_mod._cache_set(token, ctx)

    app = create_app()
    app.dependency_overrides[session_mod.get_db_session] = _mock_get_db_session
    client = TestClient(app, raise_server_exceptions=False)
    return client, token


class TestGroupReportAPI:
    """T07-04: 集团报表接口 /api/v1/group/reports/*。"""

    def test_get_report_no_snapshots(self) -> None:
        client, token = _setup_app_with_mock_db()
        enterprise = uuid4()

        response = client.get(
            f"/api/v1/group/reports/sales?enterprise_id={enterprise}",
            headers={"X-Tenant-Token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["dimension"] == "sales"
        assert data["is_delayed"] is False
        assert data["organization_count"] == 0

    def test_get_report_invalid_dimension(self) -> None:
        client, token = _setup_app_with_mock_db()
        enterprise = uuid4()

        response = client.get(
            f"/api/v1/group/reports/invalid_dim?enterprise_id={enterprise}",
            headers={"X-Tenant-Token": token},
        )
        assert response.status_code == 400

    def test_get_report_no_token(self) -> None:
        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        enterprise = uuid4()

        response = client.get(
            f"/api/v1/group/reports/sales?enterprise_id={enterprise}",
        )
        assert response.status_code == 401


class TestPropagateMasterDataAPI:
    """T07-05: 主数据下发接口。"""

    def test_propagate_success(self) -> None:
        client, token = _setup_app_with_mock_db()
        enterprise = uuid4()
        org1, org2 = uuid4(), uuid4()

        response = client.post(
            f"/api/v1/group/master-data:propagate?enterprise_id={enterprise}",
            json={
                "master_data_type": "sku",
                "master_data_id": "SKU-001",
                "changes": {"name": "商品A"},
                "target_org_ids": [str(org1), str(org2)],
            },
            headers={"X-Tenant-Token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["master_data_id"] == "SKU-001"
        assert len(data["succeeded"]) == 2
        assert data["has_conflict"] is False


class TestReadonlyCheckAPI:
    """T07-01: 只读边界校验接口。"""

    def test_readonly_check_read_allowed(self) -> None:
        client, token = _setup_app_with_mock_db()
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
        assert response.json()["enforced"] is True

    def test_readonly_check_write_rejected(self) -> None:
        client, token = _setup_app_with_mock_db()
        enterprise = uuid4()

        response = client.post(
            f"/api/v1/group/readonly-check?enterprise_id={enterprise}",
            json={
                "is_group_admin": True,
                "operation": "update",
                "target_organization_id": str(uuid4()),
            },
            headers={"X-Tenant-Token": token},
        )
        assert response.status_code == 403
        assert "EITP_MT_GROUP_READONLY_VIOLATION" in response.text
