"""T10 备份与恢复 API 集成测试。"""

from __future__ import annotations

from uuid import uuid4

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


def _setup_client() -> tuple[TestClient, str]:
    tc_mod.clear_token_cache()
    token = str(uuid4())
    ctx = TenantContext(tenant_id=uuid4())
    tc_mod._cache_set(token, ctx)
    app = create_app()
    app.dependency_overrides[session_mod.get_db_session] = _mock_get_db_session
    client = TestClient(app, raise_server_exceptions=False)
    return client, token


class TestBackupAPI:
    def test_trigger_backup(self) -> None:
        client, token = _setup_client()
        tenant = uuid4()

        response = client.post(
            f"/api/v1/platform/backup/{tenant}",
            headers={"X-Tenant-Token": token},
        )
        assert response.status_code == 202
        assert "backup_id" in response.json()

    def test_list_backups(self) -> None:
        client, token = _setup_client()
        tenant = uuid4()

        client.post(
            f"/api/v1/platform/backup/{tenant}",
            headers={"X-Tenant-Token": token},
        )

        response = client.get(
            f"/api/v1/platform/backup/{tenant}/list",
            headers={"X-Tenant-Token": token},
        )
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_set_retention_policy(self) -> None:
        client, token = _setup_client()
        tenant = uuid4()

        response = client.put(
            f"/api/v1/platform/backup/{tenant}/retention",
            json={"retain_days": 60, "retain_copies": 20},
            headers={"X-Tenant-Token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["retain_days"] == 60
        assert data["retain_copies"] == 20

    def test_restore_cross_tenant_denied(self) -> None:
        client, token = _setup_client()
        tenant = uuid4()
        other_tenant = uuid4()

        trigger_resp = client.post(
            f"/api/v1/platform/backup/{tenant}",
            headers={"X-Tenant-Token": token},
        )
        backup_id = trigger_resp.json()["backup_id"]

        response = client.post(
            f"/api/v1/platform/backup/{backup_id}/restore",
            json={"target_tenant_id": str(other_tenant)},
            headers={"X-Tenant-Token": token},
        )
        assert response.status_code == 403
        assert "EITP_MT_CROSS_TENANT_RESTORE_DENIED" in response.text