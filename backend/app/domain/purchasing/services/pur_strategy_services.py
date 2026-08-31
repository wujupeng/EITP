"""PUR 策略领域服务 - 采购→WMS/INV操作映射 + 审批路由 + 三边对账。"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.interfaces.middleware.error_handler import PURError, PURErrorCode


class PurToWmsReceivingMapper:
    """采购到货 → WMS 收货 API 映射。第一条红线：采购不直接改库存。"""

    @staticmethod
    def build_wms_receiving_params(
        tenant_id: UUID,
        order_id: UUID,
        warehouse_id: UUID,
        receiving_zone_id: UUID,
        sku_id: UUID,
        quantity: float,
        location_id: UUID,
        operated_by: UUID,
    ) -> dict:
        return {
            "tenant_id": str(tenant_id),
            "source_document_id": str(order_id),
            "source_document_type": "purchase_order",
            "warehouse_id": str(warehouse_id),
            "zone_id": str(receiving_zone_id),
            "sku_id": str(sku_id),
            "quantity": quantity,
            "location_id": str(location_id),
            "operated_by": str(operated_by),
        }


class PurToInvFinancialMapper:
    """采购结算 → INV Financial API 映射。第二条红线：采购不直接改成本。"""

    @staticmethod
    def build_inv_cost_params(
        tenant_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID,
        quantity: float,
        unit_cost: float,
        document_id: UUID,
        operated_by: UUID,
    ) -> dict:
        return {
            "tenant_id": str(tenant_id),
            "sku_id": str(sku_id),
            "warehouse_id": str(warehouse_id),
            "quantity": quantity,
            "unit_cost": unit_cost,
            "document_id": str(document_id),
            "document_type": "purchase_settlement",
            "operated_by": str(operated_by),
        }

    @staticmethod
    def build_inv_return_params(
        tenant_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID,
        quantity: float,
        document_id: UUID,
        operated_by: UUID,
    ) -> dict:
        return {
            "tenant_id": str(tenant_id),
            "sku_id": str(sku_id),
            "warehouse_id": str(warehouse_id),
            "transaction_type": "return_out",
            "quantity": quantity,
            "document_id": str(document_id),
            "document_type": "purchase_return",
            "operated_by": str(operated_by),
        }


@dataclass
class ApprovalRule:
    threshold: float
    approver_role: str


class ApprovalRouterService:
    """审批人路由服务 - 按金额阈值路由审批人。复用 MDM GovernanceWorkflow 模式。"""

    def __init__(self, rules: list[ApprovalRule] | None = None) -> None:
        self._rules = sorted(rules or [
            ApprovalRule(threshold=10000, approver_role="pur:approver_l1"),
            ApprovalRule(threshold=100000, approver_role="pur:approver_l2"),
            ApprovalRule(threshold=float("inf"), approver_role="pur:approver_l3"),
        ], key=lambda r: r.threshold)

    def route(self, amount: float) -> str:
        for rule in self._rules:
            if amount <= rule.threshold:
                return rule.approver_role
        return self._rules[-1].approver_role


class PurReconcileService:
    """采购↔WMS↔INV 三边对账服务。第六条红线。"""

    @staticmethod
    def reconcile(
        pur_received_qty: float,
        wms_position_qty: float,
        inv_on_hand_qty: float,
    ) -> dict:
        pur_wms_diff = round(pur_received_qty - wms_position_qty, 2)
        pur_inv_diff = round(pur_received_qty - inv_on_hand_qty, 2)
        wms_inv_diff = round(wms_position_qty - inv_on_hand_qty, 2)
        consistent = abs(pur_wms_diff) < 0.01 and abs(pur_inv_diff) < 0.01 and abs(wms_inv_diff) < 0.01
        if not consistent:
            raise PURError(
                PURErrorCode.WMS_INV_INCONSISTENT,
                f"采购↔WMS↔INV三边不一致: PUR={pur_received_qty} WMS={wms_position_qty} INV={inv_on_hand_qty}",
            )
        return {
            "consistent": consistent,
            "pur_received_qty": pur_received_qty,
            "wms_position_qty": wms_position_qty,
            "inv_on_hand_qty": inv_on_hand_qty,
            "pur_wms_diff": pur_wms_diff,
            "pur_inv_diff": pur_inv_diff,
            "wms_inv_diff": wms_inv_diff,
        }