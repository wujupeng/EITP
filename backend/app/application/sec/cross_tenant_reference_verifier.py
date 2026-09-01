"""CrossTenantReferenceVerifier - 跨租户引用验证器。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass
class ReferenceVerificationResult:
    reference_type: str
    target_id: UUID
    status_code: int = 0
    is_rejected: bool = False
    evidence: dict[str, Any] = field(default_factory=dict)


class CrossTenantReferenceVerifier:
    """租户 A 业务对象尝试引用租户 B 主数据，验证拒绝。"""

    def __init__(self, http_client: Any) -> None:
        self._http_client = http_client

    async def verify_reference(
        self,
        tenant_a_token: str,
        tenant_b_customer_id: UUID | None = None,
        tenant_b_supplier_id: UUID | None = None,
        tenant_b_sku_id: UUID | None = None,
    ) -> list[ReferenceVerificationResult]:
        results: list[ReferenceVerificationResult] = []
        headers = {"Authorization": f"Bearer {tenant_a_token}"}

        if tenant_b_customer_id:
            resp = await self._http_client.post(
                "/api/v1/sal/orders",
                headers=headers,
                json={"customer_id": str(tenant_b_customer_id)},
            )
            results.append(ReferenceVerificationResult(
                reference_type="customer",
                target_id=tenant_b_customer_id,
                status_code=resp.status_code,
                is_rejected=resp.status_code in (400, 403, 404),
                evidence={"response": resp.text},
            ))

        if tenant_b_supplier_id:
            resp = await self._http_client.post(
                "/api/v1/pur/orders",
                headers=headers,
                json={"supplier_id": str(tenant_b_supplier_id)},
            )
            results.append(ReferenceVerificationResult(
                reference_type="supplier",
                target_id=tenant_b_supplier_id,
                status_code=resp.status_code,
                is_rejected=resp.status_code in (400, 403, 404),
                evidence={"response": resp.text},
            ))

        if tenant_b_sku_id:
            resp = await self._http_client.post(
                "/api/v1/inv/balances",
                headers=headers,
                json={"sku_id": str(tenant_b_sku_id)},
            )
            results.append(ReferenceVerificationResult(
                reference_type="sku",
                target_id=tenant_b_sku_id,
                status_code=resp.status_code,
                is_rejected=resp.status_code in (400, 403, 404),
                evidence={"response": resp.text},
            ))

        return results