"""WMS 多租户隔离测试 - 四层纵深防护验证。

API 层 SecurityContext.tenant_id 校验 → 应用层 DataScope 收敛
→ 仓储层 TenantFilterEvent 自动追加 WHERE tenant_id → 数据库层 RLS 强制匹配

需要完整数据库环境。
"""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from app.application.e2e.wms_golden_path_e2e_suite import BASE_URL, TENANT_TOKEN, ADMIN_PASSWORD


@pytest.fixture
async def api_client():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        resp = await client.post(
            "/auth/login",
            json={"tenant_id": TENANT_TOKEN, "username": "admin", "password": ADMIN_PASSWORD},
            headers={"X-Tenant-Token": TENANT_TOKEN},
        )
        token = resp.json().get("access_token") or resp.json().get("token")
        headers = {"Authorization": f"Bearer {token}", "X-Tenant-Token": TENANT_TOKEN, "Content-Type": "application/json"}
        yield client, headers


@pytest.mark.asyncio
async def test_wms_cross_tenant_space_isolation(api_client):
    """跨租户访问仓储空间被拦截 - RLS 层强制。"""
    client, headers = api_client
    tenant_a_token = TENANT_TOKEN
    tenant_b_token = str(uuid4())

    resp_a = await client.post(
        "/wms/space/warehouses",
        json={"warehouse_code": f"WH-A-{uuid4().hex[:6]}", "warehouse_name": "租户A仓库"},
        headers={**headers, "X-Tenant-Token": tenant_a_token},
    )
    assert resp_a.status_code in (200, 201)
    wh_id = resp_a.json()["warehouse_id"]

    resp_b = await client.get(
        f"/wms/space/warehouses/{wh_id}/tree",
        headers={**headers, "X-Tenant-Token": tenant_b_token},
    )
    assert resp_b.status_code in (403, 404), f"Cross-tenant access should be denied, got {resp_b.status_code}"


@pytest.mark.asyncio
async def test_wms_cross_tenant_task_isolation(api_client):
    """跨租户访问 WMS Task 被拦截。"""
    client, headers = api_client
    resp = await client.get("/wms/tasks", headers=headers)
    assert resp.status_code == 200
    tasks_a = resp.json()

    tenant_b_token = str(uuid4())
    resp_b = await client.get(
        "/wms/tasks",
        headers={**headers, "X-Tenant-Token": tenant_b_token},
    )
    assert resp_b.status_code == 200
    tasks_b = resp_b.json()

    task_a_ids = {t.get("task_id") for t in tasks_a}
    task_b_ids = {t.get("task_id") for t in tasks_b}
    assert task_a_ids.isdisjoint(task_b_ids), "Tenant A and B should not share any tasks"


@pytest.mark.asyncio
async def test_wms_cross_tenant_position_isolation(api_client):
    """跨租户访问库存位置被拦截。"""
    client, headers = api_client
    resp = await client.get("/wms/inventory-positions", headers=headers)
    assert resp.status_code == 200

    tenant_b_token = str(uuid4())
    resp_b = await client.get(
        "/wms/inventory-positions",
        headers={**headers, "X-Tenant-Token": tenant_b_token},
    )
    assert resp_b.status_code == 200
    assert resp_b.json() == [] or all(
        p.get("tenant_id") != TENANT_TOKEN for p in resp_b.json()
    )


@pytest.mark.asyncio
async def test_wms_cross_tenant_ref_denied(api_client):
    """跨租户引用库位被拒绝 EITP_WMS_CROSS_TENANT_REF_DENIED。"""
    client, headers = api_client
    tenant_b_token = str(uuid4())

    resp_b = await client.post(
        "/wms/space/locations",
        json={"warehouse_id": str(uuid4()), "zone_id": str(uuid4()), "location_code": "X-LOC"},
        headers={**headers, "X-Tenant-Token": tenant_b_token},
    )
    assert resp_b.status_code in (400, 403, 404), f"Cross-tenant ref should be denied, got {resp_b.status_code}"


@pytest.mark.asyncio
async def test_wms_rls_enforced(api_client):
    """数据库层 RLS 强制 tenant_id 匹配 - 通过 API 验证不可见性。"""
    client, headers = api_client
    resp = await client.post(
        "/wms/space/warehouses",
        json={"warehouse_code": f"WH-RLS-{uuid4().hex[:6]}", "warehouse_name": "RLS测试仓库"},
        headers=headers,
    )
    assert resp.status_code in (200, 201)
    wh_id = resp.json()["warehouse_id"]

    tree_resp = await client.get(f"/wms/space/warehouses/{wh_id}/tree", headers=headers)
    assert tree_resp.status_code == 200

    tenant_b_token = str(uuid4())
    cross_resp = await client.get(
        f"/wms/space/warehouses/{wh_id}/tree",
        headers={**headers, "X-Tenant-Token": tenant_b_token},
    )
    assert cross_resp.status_code in (403, 404)
