"""AttackMatrixDefinition 聚合根 - 攻击矩阵定义，15 层 × 9 操作 × 55 聚合根 = 524 认证项。"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from app.domain.sec.certification.value_objects.isolation_layer import (
    IsolationLayer,
    NineOperation,
)


_AGGREGATE_ROOTS: dict[str, list[str]] = {
    "MT": ["Tenant", "Hierarchy", "Group", "Config"],
    "IAM": ["User", "Role", "Permission", "Session", "Token", "DataScope"],
    "INV": ["InventoryBalance", "InventoryLedger", "InventoryReservation", "InventoryDocument"],
    "MDM": ["EnterpriseProduct", "EnterpriseSKU", "Barcode", "Specification", "GovernanceWorkflow", "GroupCatalog", "Template", "NegativePolicy", "MasterDataAudit"],
    "WMS": ["Space", "Location", "Zone", "Area", "ReceivingOrder", "PutawayOrder", "PickingTask", "TransferOrder", "ShippingOrder", "InventoryPosition", "WmsTask", "WmsAudit", "WmsReconcile"],
    "PUR": ["Supplier", "PurchaseRequest", "PurchaseOrder", "PurchaseReceipt", "PurchaseReturn", "PurchaseSettlement", "SupplierEvaluation"],
    "SAL": ["Customer", "CustomerCategory", "CreditLimit", "CustomerPricing", "SalesQuotation", "SalesOrder", "ShipmentOrder", "PackingRecord", "SalesReturn", "SalesSettlement", "SalesInvoice", "PaymentReceipt"],
}


@dataclass
class AttackMatrixDefinition:
    matrix_id: UUID = field(default_factory=uuid4)
    matrix_version: str = "1.0"
    layers: list[IsolationLayer] = field(default_factory=lambda: list(IsolationLayer))
    operations: list[NineOperation] = field(default_factory=lambda: list(NineOperation))
    aggregate_roots: dict[str, list[str]] = field(default_factory=lambda: copy.deepcopy(_AGGREGATE_ROOTS))
    e2e_steps: int = 14

    @property
    def total_aggregate_roots(self) -> int:
        return sum(len(roots) for roots in self.aggregate_roots.values())

    @property
    def total_matrix_items(self) -> int:
        return len(self.layers) * len(self.operations) * self.total_aggregate_roots

    @property
    def total_items(self) -> int:
        return self.total_matrix_items + len(self.layers) + self.e2e_steps

    def generate_item_ids(self) -> list[str]:
        item_ids: list[str] = []
        for layer in self.layers:
            item_ids.append(f"SEC-ITEM-{layer.value}-E2E-attack_chain")
        for layer in self.layers:
            for op in self.operations:
                for module, roots in self.aggregate_roots.items():
                    for root in roots:
                        item_ids.append(f"SEC-ITEM-{layer.value}-{op.value}-{module}:{root}")
        for step in range(1, self.e2e_steps + 1):
            item_ids.append(f"SEC-ITEM-E2E-step-{step:02d}")
        return item_ids

    def get_items_by_layer(self, layer: IsolationLayer) -> list[str]:
        prefix = f"SEC-ITEM-{layer.value}-"
        return [iid for iid in self.generate_item_ids() if iid.startswith(prefix)]

    def get_items_by_module(self, module: str) -> list[str]:
        return [iid for iid in self.generate_item_ids() if f"-{module}:" in iid]