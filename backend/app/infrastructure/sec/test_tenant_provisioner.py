"""TestTenantProvisioner - 创建/清理独立测试租户与测试数据。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4


@dataclass
class TestTenantPair:
    tenant_a: UUID
    tenant_b: UUID
    created_resources: list[dict[str, Any]] = field(default_factory=list)


class TestTenantProvisioner:
    """创建独立测试租户 A/B + 测试数据，认证完成后清理。"""

    def __init__(self, http_client: Any) -> None:
        self._http_client = http_client

    async def provision(self, prefix: str = "sec-test") -> TestTenantPair:
        tenant_a = uuid4()
        tenant_b = uuid4()
        pair = TestTenantPair(tenant_a=tenant_a, tenant_b=tenant_b)

        for tenant_id in (tenant_a, tenant_b):
            resp = await self._http_client.post(
                "/api/v1/mt/tenants",
                json={
                    "tenant_id": str(tenant_id),
                    "enterprise_name": f"{prefix}-{tenant_id}",
                    "admin_username": f"admin_{prefix}",
                    "admin_password": "Test@12345",
                },
            )
            pair.created_resources.append({"type": "tenant", "id": str(tenant_id), "status": resp.status_code})

        return pair

    async def cleanup(self, pair: TestTenantPair) -> list[dict[str, Any]]:
        cleanup_results: list[dict[str, Any]] = []
        for resource in pair.created_resources:
            if resource["type"] == "tenant":
                try:
                    resp = await self._http_client.delete(f"/api/v1/mt/tenants/{resource['id']}")
                    cleanup_results.append({"id": resource["id"], "status": resp.status_code, "success": resp.status_code < 400})
                except Exception as exc:
                    cleanup_results.append({"id": resource["id"], "status": "error", "success": False, "error": str(exc)})
        return cleanup_results