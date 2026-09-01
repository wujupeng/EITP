"""ModuleCertificationOrchestrator - 7 模块多租户隔离全矩阵认证。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.domain.sec.attack_matrix.services.certification_item_executor import CertificationItemExecutor
from app.domain.sec.certification.aggregates.certification_item_aggregate import CertificationItemAggregate
from app.domain.sec.certification.value_objects.isolation_layer import Conclusion, NineOperation
from app.domain.sec.attack_matrix.value_objects.attack_vector import AttackVector
from app.domain.sec.attack_matrix.services.attack_vector_factory import AttackVectorFactory
from app.domain.sec.certification.value_objects.isolation_layer import IsolationLayer

_MODULES = ["MT", "IAM", "INV", "MDM", "WMS", "PUR", "SAL"]

_AGGREGATE_ROOTS: dict[str, list[str]] = {
    "MT": ["Tenant", "Hierarchy", "TenantMember", "DataPlacement"],
    "IAM": ["User", "Role", "Permission", "DataScope", "SecurityContext", "TokenRevocation"],
    "INV": ["InventoryBalance", "InventoryLedger", "InventoryReservation", "InventoryTransfer"],
    "MDM": ["EnterpriseSKU", "EnterpriseProduct", "GroupProduct", "Barcode", "Unit", "Category", "Brand", "Attribute", "GovernanceWorkflow"],
    "WMS": ["PickingTask", "ShippingOrder", "ReceivingOrder", "InventoryPosition", "Warehouse", "Location", "Wave", "Pack", "Sort", "Loading", "Return", "StockTake", "MoveTask"],
    "PUR": ["PurchaseOrder", "Supplier", "PurchaseQuotation", "ReceivingOrder", "PurchaseReturn", "PurchaseSettlement", "PriceComparison"],
    "SAL": ["SalesOrder", "Customer", "ShipmentOrder", "SalesReturn", "SalesSettlement", "SalesInvoice", "PaymentReceipt", "SalesQuotation", "CreditLimit", "CustomerPricing", "CustomerCategory", "SalesAudit"],
}


@dataclass
class ModuleCertificationResult:
    module: str
    total_items: int = 0
    passed: int = 0
    failed: int = 0
    unexecutable: int = 0
    items: list[CertificationItemAggregate] = field(default_factory=list)


class ModuleCertificationOrchestrator:
    """7 模块 × 9 操作 × 55 聚合根全矩阵认证。"""

    def __init__(self, http_client: Any) -> None:
        self._http_client = http_client
        self._item_executor = CertificationItemExecutor(http_client)

    async def execute_all_modules(
        self,
        batch_id: UUID,
        tenant_a: UUID,
        tenant_b: UUID,
        modules: list[str] | None = None,
    ) -> list[ModuleCertificationResult]:
        target_modules = modules or _MODULES
        results: list[ModuleCertificationResult] = []
        for module in target_modules:
            result = await self._execute_module(module, batch_id, tenant_a, tenant_b)
            results.append(result)
        return results

    async def _execute_module(
        self,
        module: str,
        batch_id: UUID,
        tenant_a: UUID,
        tenant_b: UUID,
    ) -> ModuleCertificationResult:
        aggregate_roots = _AGGREGATE_ROOTS.get(module, [])
        items: list[CertificationItemAggregate] = []
        for ar in aggregate_roots:
            for op in NineOperation:
                vector = AttackVectorFactory.create(
                    IsolationLayer.API, op, tenant_a, tenant_b, ar
                )
                item = CertificationItemAggregate(
                    item_id=f"SEC-ITEM-API-{op.value}-{ar}",
                    batch_id=batch_id,
                    layer=IsolationLayer.API,
                    operation=op,
                    aggregate_root=ar,
                    attack_vector=vector,
                    expected_behavior="blocked",
                    tenant_id=tenant_a,
                )
                items.append(item)

        executed = await self._item_executor.execute_batch(items)
        passed = sum(1 for i in executed if i.conclusion == Conclusion.PASS)
        failed = sum(1 for i in executed if i.conclusion == Conclusion.FAIL)
        unexecutable = sum(1 for i in executed if i.conclusion == Conclusion.UNEXECUTABLE)
        return ModuleCertificationResult(
            module=module,
            total_items=len(executed),
            passed=passed,
            failed=failed,
            unexecutable=unexecutable,
            items=executed,
        )