"""CrossTenantAccessVerifier - 跨租户访问验证器。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.domain.sec.certification.value_objects.isolation_layer import NineOperation

_OPERATION_HTTP_METHODS: dict[NineOperation, str] = {
    NineOperation.SELECT: "GET",
    NineOperation.INSERT: "POST",
    NineOperation.UPDATE: "PUT",
    NineOperation.DELETE: "DELETE",
    NineOperation.JOIN: "GET",
    NineOperation.AGGREGATE: "GET",
    NineOperation.COUNT: "GET",
    NineOperation.EXPORT: "GET",
    NineOperation.AUDIT: "GET",
}


@dataclass
class AccessVerificationResult:
    operation: NineOperation
    status_code: int = 0
    is_blocked: bool = False
    evidence: dict[str, Any] = field(default_factory=dict)


class CrossTenantAccessVerifier:
    """以租户 A 身份执行 9 操作访问租户 B 资源，验证拦截。"""

    def __init__(self, http_client: Any) -> None:
        self._http_client = http_client

    async def verify(
        self,
        tenant_a_token: str,
        tenant_b_resource_id: UUID,
        resource_endpoint: str,
        operations: list[NineOperation] | None = None,
    ) -> list[AccessVerificationResult]:
        target_ops = operations or list(NineOperation)
        results: list[AccessVerificationResult] = []
        for op in target_ops:
            result = await self._execute_operation(tenant_a_token, tenant_b_resource_id, resource_endpoint, op)
            results.append(result)
        return results

    async def _execute_operation(
        self,
        token: str,
        resource_id: UUID,
        endpoint: str,
        operation: NineOperation,
    ) -> AccessVerificationResult:
        method = _OPERATION_HTTP_METHODS.get(operation, "GET")
        url = f"{endpoint}/{resource_id}"
        headers = {"Authorization": f"Bearer {token}"}

        if method == "GET":
            resp = await self._http_client.get(url, headers=headers)
        elif method == "POST":
            resp = await self._http_client.post(url, headers=headers, json={})
        elif method == "PUT":
            resp = await self._http_client.put(url, headers=headers, json={})
        elif method == "DELETE":
            resp = await self._http_client.delete(url, headers=headers)
        else:
            resp = await self._http_client.get(url, headers=headers)

        is_blocked = resp.status_code in (401, 403, 404)
        return AccessVerificationResult(
            operation=operation,
            status_code=resp.status_code,
            is_blocked=is_blocked,
            evidence={"url": url, "method": method, "response": resp.text},
        )