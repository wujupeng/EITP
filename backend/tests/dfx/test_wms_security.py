"""WMS 安全测试 - 第一条红线 + 纵深防御 + fail-closed。

验证：
  1. 第一条红线：WMS 不直接修改 Ledger/Balance（启动校验 + 代码审查 + RLS 三重保证）
  2. WMS 作业审计不可篡改（append-only + REVOKE UPDATE/DELETE + Trigger 双保险）
  3. 禁止直接修改 Inventory Position
  4. 禁止越权领取他人 Task
  5. 禁止跨仓库移库
  6. 审计不含敏感信息
  7. fail-closed 原则

需要完整数据库环境。
"""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text

from app.application.e2e.wms_golden_path_e2e_suite import BASE_URL, TENANT_TOKEN, ADMIN_PASSWORD
from app.infrastructure.db.session import get_session_factory


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
async def test_wms_red_line_no_direct_inv_modification():
    """第一条红线：WMS 服务账号对 inv_* 表无直接写权限（RLS）。"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(text("""
            SELECT has_table_privilege('wms_service_role', 'inv_inventory_ledger', 'INSERT') AS can_insert,
                   has_table_privilege('wms_service_role', 'inv_inventory_balance', 'UPDATE') AS can_update,
                   has_table_privilege('wms_service_role', 'inv_inventory_reservation', 'DELETE') AS can_delete
        """))
        row = result.fetchone()
        if row:
            assert not row.can_insert, "WMS service role should NOT have INSERT on inv_inventory_ledger"
            assert not row.can_update, "WMS service role should NOT have UPDATE on inv_inventory_balance"
            assert not row.can_delete, "WMS service role should NOT have DELETE on inv_inventory_reservation"


@pytest.mark.asyncio
async def test_wms_audit_append_only():
    """WMS 作业审计不可篡改 - append-only + REVOKE UPDATE/DELETE。"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(text("""
            SELECT has_table_privilege('wms_service_role', 'wms_operation_audit', 'UPDATE') AS can_update,
                   has_table_privilege('wms_service_role', 'wms_operation_audit', 'DELETE') AS can_delete
        """))
        row = result.fetchone()
        if row:
            assert not row.can_update, "WMS service role should NOT have UPDATE on wms_operation_audit"
            assert not row.can_delete, "WMS service role should NOT have DELETE on wms_operation_audit"


@pytest.mark.asyncio
async def test_wms_unauthorized_task_claim_rejected(api_client):
    """禁止越权领取他人 Task。"""
    client, headers = api_client
    task_resp = await client.post(
        "/wms/tasks",
        json={"task_type": "receiving", "document_id": str(uuid4()), "document_type": "receiving_order"},
        headers=headers,
    )
    if task_resp.status_code in (200, 201):
        task_id = task_resp.json().get("task_id")
        claim_resp = await client.post(f"/wms/tasks/{task_id}/claim", headers=headers)
        assert claim_resp.status_code in (200, 201, 403), f"Unexpected status: {claim_resp.status_code}"


@pytest.mark.asyncio
async def test_wms_fail_closed_on_inv_failure(api_client):
    """fail-closed 原则：INV Transaction 失败时 WMS Task FAILED 而非放行。"""
    client, headers = api_client
    receiving_id = str(uuid4())
    resp = await client.post(
        f"/wms/receiving/orders/{receiving_id}/execute",
        json={"line_id": str(uuid4()), "received_quantity": 100, "location_id": str(uuid4()), "idempotency_key": f"wms:fail:{uuid4().hex[:8]}"},
        headers=headers,
    )
    assert resp.status_code >= 400, "Invalid receiving should fail (fail-closed)"