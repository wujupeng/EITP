"""T08 主数据 API 集成测试。"""

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


class TestMasterDataAPI:
    def test_create_sku(self) -> None:
        client, token = _setup_client()
        enterprise = uuid4()

        response = client.post(
            "/api/v1/master-data/sku",
            json={
                "enterprise_id": str(enterprise),
                "sku_code": "SKU-001",
                "base_attrs": {"name": "商品A", "price": 50},
            },
            headers={"X-Tenant-Token": token},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["sku_code"] == "SKU-001"
        assert data["version"] == 1

    def test_create_sku_no_token(self) -> None:
        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        enterprise = uuid4()

        response = client.post(
            "/api/v1/master-data/sku",
            json={
                "enterprise_id": str(enterprise),
                "sku_code": "SKU-001",
                "base_attrs": {},
            },
        )
        assert response.status_code == 401

    def test_update_sku_base_readonly_rejected(self) -> None:
        client, token = _setup_client()
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

    def test_get_effective_no_token(self) -> None:
        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        sku_id = uuid4()

        response = client.get(f"/api/v1/master-data/sku/{sku_id}/effective")
        assert response.status_code == 401