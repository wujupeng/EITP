"""T09 数据放置与迁移 API 集成测试。"""

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


class TestPlacementAPI:
    def test_set_placement(self) -> None:
        client, token = _setup_client()
        tenant = uuid4()

        response = client.put(
            f"/api/v1/platform/placement/{tenant}",
            json={"placement": "dedicated_db"},
            headers={"X-Tenant-Token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["placement"] == "dedicated_db"

    def test_set_placement_invalid(self) -> None:
        client, token = _setup_client()
        tenant = uuid4()

        response = client.put(
            f"/api/v1/platform/placement/{tenant}",
            json={"placement": "invalid_mode"},
            headers={"X-Tenant-Token": token},
        )
        assert response.status_code == 400

    def test_get_placement(self) -> None:
        client, token = _setup_client()
        tenant = uuid4()

        client.put(
            f"/api/v1/platform/placement/{tenant}",
            json={"placement": "shared_db"},
            headers={"X-Tenant-Token": token},
        )

        response = client.get(
            f"/api/v1/platform/placement/{tenant}",
            headers={"X-Tenant-Token": token},
        )
        assert response.status_code == 200
        assert response.json()["placement"] == "shared_db"

    def test_get_placement_not_found(self) -> None:
        client, token = _setup_client()
        tenant = uuid4()

        response = client.get(
            f"/api/v1/platform/placement/{tenant}",
            headers={"X-Tenant-Token": token},
        )
        assert response.status_code == 404

    def test_migrate(self) -> None:
        client, token = _setup_client()
        tenant = uuid4()

        response = client.post(
            f"/api/v1/platform/placement/{tenant}/migrate",
            json={
                "target_placement": "dedicated_db",
                "maintenance_window": "2026-01-01T02:00:00/2026-01-01T04:00:00",
            },
            headers={"X-Tenant-Token": token},
        )
        assert response.status_code == 202
        data = response.json()
        assert "migration_task_id" in data
        assert data["phase"] == "pending"

    def test_migrate_status(self) -> None:
        client, token = _setup_client()
        tenant = uuid4()

        migrate_resp = client.post(
            f"/api/v1/platform/placement/{tenant}/migrate",
            json={
                "target_placement": "dedicated_db",
                "maintenance_window": "2026-01-01T02:00:00/2026-01-01T04:00:00",
            },
            headers={"X-Tenant-Token": token},
        )
        task_id = migrate_resp.json()["migration_task_id"]

        response = client.get(
            f"/api/v1/platform/placement/{tenant}/migrate/{task_id}/status",
            headers={"X-Tenant-Token": token},
        )
        assert response.status_code == 200
        assert response.json()["phase"] == "pending"