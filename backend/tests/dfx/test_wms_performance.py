"""WMS 性能测试 - spec 4.1 DFX 性能指标验证。

指标：
  仓储空间查询 P95 ≤ 200ms
  库存位置查询 P95 ≤ 150ms
  库位定位 SKU P95 ≤ 50ms
  WMS Task 创建 P95 ≤ 300ms
  拣货任务生成 P95 ≤ 500ms
  上架库位建议 P95 ≤ 300ms
  WMS 作业执行 P95 ≤ 1s
  单仓库并发作业 ≥ 200 TPS
  PDA 并发扫码 ≥ 100 TPS
  库存位置查询 ≥ 500 QPS

需要完整数据库环境。
"""

from __future__ import annotations

import time
from uuid import uuid4

import httpx
import pytest

from app.application.e2e.wms_golden_path_e2e_suite import BASE_URL, TENANT_TOKEN, ADMIN_PASSWORD

P95_SPACE_QUERY_MS = 200
P95_POSITION_QUERY_MS = 150
P95_TASK_CREATE_MS = 300
P95_OPERATION_EXECUTE_MS = 1000


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


def _p95(durations: list[float]) -> float:
    if not durations:
        return 0.0
    sorted_d = sorted(durations)
    idx = int(len(sorted_d) * 0.95)
    return sorted_d[min(idx, len(sorted_d) - 1)]


@pytest.mark.asyncio
async def test_wms_space_query_p95(api_client):
    """仓储空间查询 P95 ≤ 200ms。"""
    client, headers = api_client
    wh_resp = await client.post(
        "/wms/space/warehouses",
        json={"warehouse_code": f"WH-PERF-{uuid4().hex[:6]}", "warehouse_name": "性能测试仓库"},
        headers=headers,
    )
    wh_id = wh_resp.json()["warehouse_id"]

    durations = []
    for _ in range(50):
        start = time.monotonic()
        await client.get(f"/wms/space/warehouses/{wh_id}/tree", headers=headers)
        durations.append((time.monotonic() - start) * 1000)

    p95 = _p95(durations)
    assert p95 <= P95_SPACE_QUERY_MS, f"Space query P95={p95:.1f}ms > {P95_SPACE_QUERY_MS}ms"


@pytest.mark.asyncio
async def test_wms_position_query_p95(api_client):
    """库存位置查询 P95 ≤ 150ms。"""
    client, headers = api_client
    durations = []
    for _ in range(50):
        start = time.monotonic()
        await client.get("/wms/inventory-positions", headers=headers)
        durations.append((time.monotonic() - start) * 1000)

    p95 = _p95(durations)
    assert p95 <= P95_POSITION_QUERY_MS, f"Position query P95={p95:.1f}ms > {P95_POSITION_QUERY_MS}ms"


@pytest.mark.asyncio
async def test_wms_task_create_p95(api_client):
    """WMS Task 创建 P95 ≤ 300ms。"""
    client, headers = api_client
    durations = []
    for _ in range(30):
        start = time.monotonic()
        await client.post(
            "/wms/tasks",
            json={"task_type": "receiving", "document_id": str(uuid4()), "document_type": "receiving_order", "priority": "medium"},
            headers=headers,
        )
        durations.append((time.monotonic() - start) * 1000)

    p95 = _p95(durations)
    assert p95 <= P95_TASK_CREATE_MS, f"Task create P95={p95:.1f}ms > {P95_TASK_CREATE_MS}ms"