"""PUR 多租户隔离测试 - 四层纵深防护验证。

API 层 SecurityContext.tenant_id 校验 → 应用层 DataScope 收敛
→ 仓储层 TenantFilterEvent 自动追加 WHERE tenant_id → 数据库层 RLS 强制匹配

需要完整数据库环境。
"""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from app.application.e2e.pur_golden_path_e2e_suite import BASE_URL, TENANT_TOKEN, ADMIN_PASSWORD


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
async def test_pur_cross_tenant_supplier_isolation(api_client):
    """跨租户访问供应商被拦截 - RLS 层强制。"""
    client, headers = api_client
    tenant_b_token = str(uuid4())

    resp_a = await client.post(
        "/pur/suppliers",
        json={"supplier_code": f"SUP-A-{uuid4().hex[:6]}", "supplier_name": "租户A供应商"},
        headers={**headers, "X-Tenant-Token": TENANT_TOKEN},
    )
    assert resp_a.status_code in (200, 201)
    supplier_id = resp_a.json()["supplier_id"]

    resp_b = await client.get(
        f"/pur/suppliers/{supplier_id}",
        headers={**headers, "X-Tenant-Token": tenant_b_token},
    )
    assert resp_b.status_code in (403, 404), f"Cross-tenant access should be denied, got {resp_b.status_code}"


@pytest.mark.asyncio
async def test_pur_cross_tenant_order_isolation(api_client):
    """跨租户访问采购订单被拦截。"""
    client, headers = api_client
    tenant_b_token = str(uuid4())

    resp_sup = await client.post(
        "/pur/suppliers",
        json={"supplier_code": f"SUP-O-{uuid4().hex[:6]}", "supplier_name": "订单隔离供应商"},
        headers={**headers, "X-Tenant-Token": TENANT_TOKEN},
    )
    assert resp_sup.status_code in (200, 201)
    supplier_id = resp_sup.json()["supplier_id"]

    resp_a = await client.post(
        "/pur/orders",
        json={"order_code": f"PO-A-{uuid4().hex[:6]}", "supplier_id": supplier_id, "lines": []},
        headers={**headers, "X-Tenant-Token": TENANT_TOKEN},
    )
    assert resp_a.status_code in (200, 201)
    order_id = resp_a.json()["order_id"]

    resp_b = await client.get(
        f"/pur/orders/{order_id}",
        headers={**headers, "X-Tenant-Token": tenant_b_token},
    )
    assert resp_b.status_code in (403, 404), f"Cross-tenant order access should be denied"


@pytest.mark.asyncio
async def test_pur_same_tenant_supplier_access(api_client):
    """同租户访问供应商正常。"""
    client, headers = api_client

    resp = await client.post(
        "/pur/suppliers",
        json={"supplier_code": f"SUP-S-{uuid4().hex[:6]}", "supplier_name": "同租户供应商"},
        headers=headers,
    )
    assert resp.status_code in (200, 201)
    supplier_id = resp.json()["supplier_id"]

    resp2 = await client.get(f"/pur/suppliers/{supplier_id}", headers=headers)
    assert resp2.status_code == 200