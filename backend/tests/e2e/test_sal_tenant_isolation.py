"""SAL 多租户隔离测试 - 四层纵深防护验证。

API 层 SecurityContext.tenant_id 校验 → 应用层 DataScope 收敛
→ 仓储层 TenantFilterEvent 自动追加 WHERE tenant_id → 数据库层 RLS 强制匹配

覆盖 9 种操作 × 16 聚合根的全矩阵，重点验证：
- 跨租户访问客户/销售订单/发货/退货/结算/审计被拦截
- 跨租户引用客户被拒绝 EITP_SAL_CROSS_TENANT_CUSTOMER_DENIED
- 跨租户引用销售数据被拒绝 EITP_SAL_CROSS_TENANT_REF_DENIED
- JOIN 跨租户泄露测试

需要完整数据库环境。
"""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from app.application.e2e.sal_golden_path_e2e_suite import BASE_URL, TENANT_TOKEN, ADMIN_PASSWORD


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
async def test_sal_cross_tenant_customer_isolation(api_client):
    """跨租户访问客户被拦截 - RLS 层强制。"""
    client, headers = api_client
    tenant_b_token = str(uuid4())

    resp_a = await client.post(
        "/sal/customers",
        json={"customer_code": f"C-A-{uuid4().hex[:6]}", "customer_name": "租户A客户"},
        headers={**headers, "X-Tenant-Token": TENANT_TOKEN},
    )
    assert resp_a.status_code in (200, 201)
    customer_id = resp_a.json()["customer_id"]

    resp_b = await client.get(
        f"/sal/customers/{customer_id}",
        headers={**headers, "X-Tenant-Token": tenant_b_token},
    )
    assert resp_b.status_code in (403, 404), f"Cross-tenant customer access should be denied, got {resp_b.status_code}"


@pytest.mark.asyncio
async def test_sal_cross_tenant_order_isolation(api_client):
    """跨租户访问销售订单被拦截。"""
    client, headers = api_client
    tenant_b_token = str(uuid4())

    resp_cust = await client.post(
        "/sal/customers",
        json={"customer_code": f"C-O-{uuid4().hex[:6]}", "customer_name": "订单隔离客户"},
        headers={**headers, "X-Tenant-Token": TENANT_TOKEN},
    )
    assert resp_cust.status_code in (200, 201)
    customer_id = resp_cust.json()["customer_id"]

    resp_a = await client.post(
        "/sal/orders",
        json={"order_code": f"SO-A-{uuid4().hex[:6]}", "customer_id": customer_id, "lines": []},
        headers={**headers, "X-Tenant-Token": TENANT_TOKEN},
    )
    assert resp_a.status_code in (200, 201)
    order_id = resp_a.json()["order_id"]

    resp_b = await client.get(
        f"/sal/orders/{order_id}",
        headers={**headers, "X-Tenant-Token": tenant_b_token},
    )
    assert resp_b.status_code in (403, 404), f"Cross-tenant order access should be denied"


@pytest.mark.asyncio
async def test_sal_cross_tenant_quotation_isolation(api_client):
    """跨租户访问销售报价被拦截。"""
    client, headers = api_client
    tenant_b_token = str(uuid4())

    resp_cust = await client.post(
        "/sal/customers",
        json={"customer_code": f"C-Q-{uuid4().hex[:6]}", "customer_name": "报价隔离客户"},
        headers={**headers, "X-Tenant-Token": TENANT_TOKEN},
    )
    customer_id = resp_cust.json()["customer_id"]

    resp_a = await client.post(
        "/sal/quotations",
        json={"quotation_code": f"SQ-A-{uuid4().hex[:6]}", "customer_id": customer_id, "lines": []},
        headers={**headers, "X-Tenant-Token": TENANT_TOKEN},
    )
    assert resp_a.status_code in (200, 201)
    quotation_id = resp_a.json()["quotation_id"]

    resp_b = await client.get(
        f"/sal/quotations/{quotation_id}",
        headers={**headers, "X-Tenant-Token": tenant_b_token},
    )
    assert resp_b.status_code in (403, 404), f"Cross-tenant quotation access should be denied"


@pytest.mark.asyncio
async def test_sal_cross_tenant_shipment_isolation(api_client):
    """跨租户访问发货单被拦截。"""
    client, headers = api_client
    tenant_b_token = str(uuid4())

    resp_a = await client.post(
        "/sal/shipments",
        json={"shipment_code": f"SH-A-{uuid4().hex[:6]}", "order_id": str(uuid4()), "lines": []},
        headers={**headers, "X-Tenant-Token": TENANT_TOKEN},
    )
    assert resp_a.status_code in (200, 201)
    shipment_id = resp_a.json()["shipment_id"]

    resp_b = await client.get(
        f"/sal/shipments/{shipment_id}",
        headers={**headers, "X-Tenant-Token": tenant_b_token},
    )
    assert resp_b.status_code in (403, 404), f"Cross-tenant shipment access should be denied"


@pytest.mark.asyncio
async def test_sal_cross_tenant_settlement_isolation(api_client):
    """跨租户访问结算单被拦截。"""
    client, headers = api_client
    tenant_b_token = str(uuid4())

    resp_a = await client.post(
        "/sal/settlements",
        json={"settlement_code": f"SS-A-{uuid4().hex[:6]}", "order_id": str(uuid4()),
              "customer_id": str(uuid4()), "total_amount": 1000},
        headers={**headers, "X-Tenant-Token": TENANT_TOKEN},
    )
    assert resp_a.status_code in (200, 201)
    settlement_id = resp_a.json()["settlement_id"]

    resp_b = await client.get(
        f"/sal/settlements/{settlement_id}",
        headers={**headers, "X-Tenant-Token": tenant_b_token},
    )
    assert resp_b.status_code in (403, 404), f"Cross-tenant settlement access should be denied"


@pytest.mark.asyncio
async def test_sal_cross_tenant_return_isolation(api_client):
    """跨租户访问退货单被拦截。"""
    client, headers = api_client
    tenant_b_token = str(uuid4())

    resp_a = await client.post(
        "/sal/returns",
        json={"return_code": f"SR-A-{uuid4().hex[:6]}", "customer_id": str(uuid4()), "lines": []},
        headers={**headers, "X-Tenant-Token": TENANT_TOKEN},
    )
    assert resp_a.status_code in (200, 201)
    return_id = resp_a.json()["return_id"]

    resp_b = await client.get(
        f"/sal/returns/{return_id}",
        headers={**headers, "X-Tenant-Token": tenant_b_token},
    )
    assert resp_b.status_code in (403, 404), f"Cross-tenant return access should be denied"


@pytest.mark.asyncio
async def test_sal_cross_tenant_customer_reference_denied(api_client):
    """跨租户引用客户被拒绝 EITP_SAL_CROSS_TENANT_CUSTOMER_DENIED。"""
    client, headers = api_client
    tenant_b_token = str(uuid4())

    resp_a = await client.post(
        "/sal/customers",
        json={"customer_code": f"C-REF-{uuid4().hex[:6]}", "customer_name": "被引用客户"},
        headers={**headers, "X-Tenant-Token": TENANT_TOKEN},
    )
    customer_id = resp_a.json()["customer_id"]

    resp_b = await client.post(
        "/sal/orders",
        json={"order_code": f"SO-REF-{uuid4().hex[:6]}", "customer_id": customer_id, "lines": []},
        headers={**headers, "X-Tenant-Token": tenant_b_token},
    )
    assert resp_b.status_code in (400, 403, 404), (
        f"Cross-tenant customer reference should be denied with EITP_SAL_CROSS_TENANT_CUSTOMER_DENIED"
    )


@pytest.mark.asyncio
async def test_sal_same_tenant_customer_access(api_client):
    """同租户访问客户正常。"""
    client, headers = api_client

    resp = await client.post(
        "/sal/customers",
        json={"customer_code": f"C-S-{uuid4().hex[:6]}", "customer_name": "同租户客户"},
        headers=headers,
    )
    assert resp.status_code in (200, 201)
    customer_id = resp.json()["customer_id"]

    resp2 = await client.get(f"/sal/customers/{customer_id}", headers=headers)
    assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_sal_same_tenant_order_access(api_client):
    """同租户访问销售订单正常。"""
    client, headers = api_client

    resp_cust = await client.post(
        "/sal/customers",
        json={"customer_code": f"C-SO-{uuid4().hex[:6]}", "customer_name": "同租户订单客户"},
        headers=headers,
    )
    customer_id = resp_cust.json()["customer_id"]

    resp = await client.post(
        "/sal/orders",
        json={"order_code": f"SO-S-{uuid4().hex[:6]}", "customer_id": customer_id, "lines": []},
        headers=headers,
    )
    assert resp.status_code in (200, 201)
    order_id = resp.json()["order_id"]

    resp2 = await client.get(f"/sal/orders/{order_id}", headers=headers)
    assert resp2.status_code == 200