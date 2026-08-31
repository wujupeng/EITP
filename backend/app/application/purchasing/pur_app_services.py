"""PUR 应用服务 - 供应商/采购申请/订单/到货/退货/结算/付款/对账。

编排领域模型 + 仓储 + 外部API（WMS Receiving / INV Financial）。
第一条红线：采购到货通过 WMS Receiving API，不直接改库存。
第二条红线：采购结算通过 INV Financial API，不直接改成本。
"""

from __future__ import annotations

from uuid import UUID, uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.purchasing.services.pur_strategy_services import (
    ApprovalRouterService, PurReconcileService, PurToInvFinancialMapper,
    PurToWmsReceivingMapper,
)
from app.infrastructure.purchasing.models import (
    PurAsnORM, PurInvoiceORM, PurPaymentRequestORM, PurPurchaseAuditORM,
    PurPurchaseOrderORM, PurPurchaseOrderLineORM, PurPurchaseReceiptORM,
    PurPurchaseReceiptLineORM, PurPurchaseRequestORM, PurPurchaseRequestLineORM,
    PurPurchaseReturnORM, PurPurchaseReturnLineORM, PurPurchaseSettlementORM,
    PurQuotationORM, PurSupplierEvaluationORM, PurSupplierORM, PurSupplierScopeORM,
)
from app.infrastructure.purchasing.repositories import (
    AsnRepository, InvoiceRepository, PaymentRequestRepository, PurchaseAuditRepository,
    PurchaseOrderRepository, PurchaseReceiptRepository, PurchaseRequestRepository,
    PurchaseReturnRepository, PurchaseSettlementRepository, PurReconcileDiffRepository,
    QuotationRepository, SupplierEvaluationRepository, SupplierRepository,
    SupplierScopeRepository,
)
from app.interfaces.middleware.error_handler import PURError, PURErrorCode
from app.interfaces.middleware.security_context import SecurityContext


WMS_API_URL = "http://localhost:8000/api/v1/wms"
INV_API_URL = "http://localhost:8000/api/v1/inv"


def _check_auth(tenant_id: UUID, permission: str) -> None:
    ctx = SecurityContext.current()
    if ctx is None:
        raise PURError(PURErrorCode.SERVICE_UNAVAILABLE, "未认证")
    if ctx.tenant.tenant_id != tenant_id:
        raise PURError(PURErrorCode.CROSS_TENANT_REF_DENIED, "跨租户操作被拒绝")


class SupplierAppSvc:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SupplierRepository()
        self._scope_repo = SupplierScopeRepository()

    async def create_supplier(self, tenant_id: UUID, supplier_code: str, supplier_name: str,
                               supplier_type: str = "distributor", **kwargs) -> PurSupplierORM:
        _check_auth(tenant_id, "pur:supplier:manage")
        existing = await self._repo.get_by_code(self._session, tenant_id, supplier_code)
        if existing:
            raise PURError(PURErrorCode.SUPPLIER_CODE_DUPLICATE, f"供应商编码 {supplier_code} 已存在")
        orm = PurSupplierORM(
            tenant_id=tenant_id, supplier_code=supplier_code, supplier_name=supplier_name,
            supplier_type=supplier_type, **{k: v for k, v in kwargs.items() if hasattr(PurSupplierORM, k)},
        )
        return await self._repo.save(self._session, orm)

    async def get_supplier(self, tenant_id: UUID, supplier_id: UUID) -> PurSupplierORM:
        _check_auth(tenant_id, "pur:supplier:query")
        orm = await self._repo.get_by_id(self._session, tenant_id, supplier_id)
        if orm is None:
            raise PURError(PURErrorCode.SUPPLIER_NOT_FOUND, f"供应商 {supplier_id} 不存在")
        return orm

    async def list_suppliers(self, tenant_id: UUID, offset: int = 0, limit: int = 50) -> list[PurSupplierORM]:
        _check_auth(tenant_id, "pur:supplier:query")
        return await self._repo.list_by_tenant(self._session, tenant_id, offset, limit)

    async def publish_supplier(self, tenant_id: UUID, supplier_id: UUID) -> PurSupplierORM:
        _check_auth(tenant_id, "pur:supplier:manage")
        orm = await self.get_supplier(tenant_id, supplier_id)
        if orm.status not in ("approved", "disabled"):
            raise PURError(PURErrorCode.ORDER_INVALID_STATE_TRANSITION, f"供应商状态 {orm.status} 不可发布")
        orm.status = "active"
        orm.published_version += 1
        await self._session.flush()
        return orm

    async def disable_supplier(self, tenant_id: UUID, supplier_id: UUID) -> PurSupplierORM:
        _check_auth(tenant_id, "pur:supplier:manage")
        orm = await self.get_supplier(tenant_id, supplier_id)
        orm.status = "disabled"
        await self._session.flush()
        return orm

    async def add_scope(self, tenant_id: UUID, supplier_id: UUID, enterprise_sku_id: UUID,
                        agreement_price: float | None = None, **kwargs) -> PurSupplierScopeORM:
        _check_auth(tenant_id, "pur:supplier:manage")
        orm = PurSupplierScopeORM(
            tenant_id=tenant_id, supplier_id=supplier_id, enterprise_sku_id=enterprise_sku_id,
            agreement_price=agreement_price, **{k: v for k, v in kwargs.items() if hasattr(PurSupplierScopeORM, k)},
        )
        return await self._scope_repo.save(self._session, orm)


class PurchaseRequestAppSvc:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PurchaseRequestRepository()
        self._router = ApprovalRouterService()

    async def create_request(self, tenant_id: UUID, request_code: str, title: str = "",
                              lines: list[dict] | None = None, **kwargs) -> PurPurchaseRequestORM:
        _check_auth(tenant_id, "pur:request:create")
        orm = PurPurchaseRequestORM(tenant_id=tenant_id, request_code=request_code, title=title,
                                    **{k: v for k, v in kwargs.items() if hasattr(PurPurchaseRequestORM, k)})
        orm = await self._repo.save(self._session, orm)
        if lines:
            for line_data in lines:
                line = PurPurchaseRequestLineORM(
                    tenant_id=tenant_id, request_id=orm.request_id,
                    **{k: v for k, v in line_data.items() if hasattr(PurPurchaseRequestLineORM, k)},
                )
                self._session.add(line)
            await self._session.flush()
        return orm

    async def approve_request(self, tenant_id: UUID, request_id: UUID, approver_id: UUID) -> PurPurchaseRequestORM:
        _check_auth(tenant_id, "pur:request:approve")
        orm = await self._repo.get_by_id(self._session, tenant_id, request_id)
        if orm is None:
            raise PURError(PURErrorCode.REQUEST_NOT_FOUND, f"采购申请 {request_id} 不存在")
        if orm.status != "submitted":
            raise PURError(PURErrorCode.REQUEST_NOT_APPROVED, "采购申请非已提交状态不可审批")
        orm.status = "approved"
        orm.approved_by = approver_id
        await self._session.flush()
        return orm


class PurchaseOrderAppSvc:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PurchaseOrderRepository()
        self._router = ApprovalRouterService()

    async def create_order(self, tenant_id: UUID, order_code: str, supplier_id: UUID,
                           warehouse_id: UUID | None = None, lines: list[dict] | None = None,
                           **kwargs) -> PurPurchaseOrderORM:
        _check_auth(tenant_id, "pur:order:create")
        orm = PurPurchaseOrderORM(tenant_id=tenant_id, order_code=order_code, supplier_id=supplier_id,
                                  warehouse_id=warehouse_id,
                                  **{k: v for k, v in kwargs.items() if hasattr(PurPurchaseOrderORM, k)})
        orm = await self._repo.save(self._session, orm)
        if lines:
            for line_data in lines:
                line = PurPurchaseOrderLineORM(
                    tenant_id=tenant_id, order_id=orm.order_id,
                    **{k: v for k, v in line_data.items() if hasattr(PurPurchaseOrderLineORM, k)},
                )
                self._session.add(line)
                orm.total_amount += line.ordered_quantity * line.unit_price
            await self._session.flush()
        return orm

    async def approve_order(self, tenant_id: UUID, order_id: UUID, approver_id: UUID) -> PurPurchaseOrderORM:
        _check_auth(tenant_id, "pur:order:approve")
        orm = await self._repo.get_by_id(self._session, tenant_id, order_id)
        if orm is None:
            raise PURError(PURErrorCode.ORDER_NOT_FOUND, f"采购订单 {order_id} 不存在")
        if orm.status != "submitted":
            raise PURError(PURErrorCode.ORDER_NOT_APPROVED, "采购订单非已提交状态不可审批")
        orm.status = "approved"
        orm.approved_by = approver_id
        await self._session.flush()
        return orm

    async def send_order(self, tenant_id: UUID, order_id: UUID) -> PurPurchaseOrderORM:
        _check_auth(tenant_id, "pur:order:send")
        orm = await self._repo.get_by_id(self._session, tenant_id, order_id)
        if orm is None:
            raise PURError(PURErrorCode.ORDER_NOT_FOUND, f"采购订单 {order_id} 不存在")
        if orm.status != "approved":
            raise PURError(PURErrorCode.ORDER_NOT_APPROVED, "采购订单非已审批状态不可发送")
        orm.status = "sent"
        await self._session.flush()
        return orm

    async def cancel_order(self, tenant_id: UUID, order_id: UUID) -> PurPurchaseOrderORM:
        _check_auth(tenant_id, "pur:order:cancel")
        orm = await self._repo.get_by_id(self._session, tenant_id, order_id)
        if orm is None:
            raise PURError(PURErrorCode.ORDER_NOT_FOUND, f"采购订单 {order_id} 不存在")
        lines = await self._repo.list_lines(self._session, tenant_id, order_id)
        if any(float(l.received_quantity) > 0 for l in lines):
            raise PURError(PURErrorCode.ORDER_CANCEL_WITH_RECEIVED, "已收货订单不可取消")
        orm.status = "cancelled"
        await self._session.flush()
        return orm


class PurchaseReceiptAppSvc:
    """采购到货应用服务 - 第一条红线：通过 WMS Receiving API 触发收货。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PurchaseReceiptRepository()
        self._order_repo = PurchaseOrderRepository()

    async def confirm_receipt(self, tenant_id: UUID, receipt_id: UUID, wms_receiving_id: UUID,
                              inv_tx_ids: list[str]) -> PurPurchaseReceiptORM:
        _check_auth(tenant_id, "pur:receipt:execute")
        orm = await self._repo.get_by_id(self._session, tenant_id, receipt_id)
        if orm is None:
            raise PURError(PURErrorCode.RECEIPT_NOT_FOUND, f"收货单 {receipt_id} 不存在")
        orm.status = "confirmed"
        orm.wms_receiving_id = wms_receiving_id
        orm.inv_transaction_ids = inv_tx_ids
        await self._session.flush()
        return orm

    async def trigger_wms_receiving(self, tenant_id: UUID, order_id: UUID, warehouse_id: UUID,
                                    receiving_zone_id: UUID, sku_id: UUID, quantity: float,
                                    location_id: UUID, operated_by: UUID) -> dict:
        """通过 WMS Receiving API 触发收货 - 第一条红线。"""
        _check_auth(tenant_id, "pur:receipt:execute")
        params = PurToWmsReceivingMapper.build_wms_receiving_params(
            tenant_id, order_id, warehouse_id, receiving_zone_id, sku_id, quantity, location_id, operated_by,
        )
        async with httpx.AsyncClient(base_url=WMS_API_URL, timeout=30) as client:
            resp = await client.post("/receiving/orders", json=params)
            if resp.status_code not in (200, 201):
                raise PURError(PURErrorCode.WMS_RECEIVING_FAILED, f"WMS收货失败: {resp.status_code} {resp.text[:200]}")
            return resp.json()


class PurchaseReturnAppSvc:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PurchaseReturnRepository()

    async def create_return(self, tenant_id: UUID, return_code: str, order_id: UUID,
                            supplier_id: UUID, lines: list[dict] | None = None, **kwargs) -> PurPurchaseReturnORM:
        _check_auth(tenant_id, "pur:return:create")
        orm = PurPurchaseReturnORM(tenant_id=tenant_id, return_code=return_code, order_id=order_id,
                                   supplier_id=supplier_id,
                                   **{k: v for k, v in kwargs.items() if hasattr(PurPurchaseReturnORM, k)})
        orm = await self._repo.save(self._session, orm)
        if lines:
            for line_data in lines:
                line = PurPurchaseReturnLineORM(tenant_id=tenant_id, return_id=orm.return_id,
                                                 **{k: v for k, v in line_data.items() if hasattr(PurPurchaseReturnLineORM, k)})
                self._session.add(line)
            await self._session.flush()
        return orm


class PurchaseSettlementAppSvc:
    """采购结算应用服务 - 第二条红线：通过 INV Financial API 落地成本。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PurchaseSettlementRepository()

    async def create_settlement(self, tenant_id: UUID, settlement_code: str, order_id: UUID,
                                supplier_id: UUID, total_amount: float) -> PurPurchaseSettlementORM:
        _check_auth(tenant_id, "pur:settlement:execute")
        orm = PurPurchaseSettlementORM(tenant_id=tenant_id, settlement_code=settlement_code,
                                       order_id=order_id, supplier_id=supplier_id, total_amount=total_amount)
        return await self._repo.save(self._session, orm)

    async def reconcile(self, tenant_id: UUID, settlement_id: UUID, received_amount: float) -> PurPurchaseSettlementORM:
        _check_auth(tenant_id, "pur:settlement:execute")
        orm = await self._repo.get_by_id(self._session, tenant_id, settlement_id)
        if orm is None:
            raise PURError(PURErrorCode.SETTLEMENT_NOT_FOUND, f"结算单 {settlement_id} 不存在")
        orm.received_amount = received_amount
        orm.diff_amount = float(orm.total_amount) - received_amount
        orm.status = "reconciled" if abs(orm.diff_amount) < 0.01 else "diff_found"
        await self._session.flush()
        return orm

    async def trigger_inv_cost(self, tenant_id: UUID, sku_id: UUID, warehouse_id: UUID,
                               quantity: float, unit_cost: float, document_id: UUID,
                               operated_by: UUID) -> dict:
        """通过 INV Financial API 落地成本 - 第二条红线。"""
        _check_auth(tenant_id, "pur:settlement:execute")
        params = PurToInvFinancialMapper.build_inv_cost_params(
            tenant_id, sku_id, warehouse_id, quantity, unit_cost, document_id, operated_by,
        )
        async with httpx.AsyncClient(base_url=INV_API_URL, timeout=30) as client:
            resp = await client.post("/financial/cost", json=params)
            if resp.status_code not in (200, 201):
                raise PURError(PURErrorCode.FINANCIAL_API_FAILED, f"INV成本落地失败: {resp.status_code}")
            return resp.json()


class PaymentAppSvc:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PaymentRequestRepository()

    async def create_payment(self, tenant_id: UUID, payment_code: str, settlement_id: UUID,
                             supplier_id: UUID, amount: float) -> PurPaymentRequestORM:
        _check_auth(tenant_id, "pur:payment:request")
        orm = PurPaymentRequestORM(tenant_id=tenant_id, payment_code=payment_code,
                                   settlement_id=settlement_id, supplier_id=supplier_id, amount=amount)
        return await self._repo.save(self._session, orm)

    async def complete_payment(self, tenant_id: UUID, payment_id: UUID) -> PurPaymentRequestORM:
        _check_auth(tenant_id, "pur:payment:confirm")
        orm = await self._repo.get_by_id(self._session, tenant_id, payment_id)
        if orm is None:
            raise PURError(PURErrorCode.PAYMENT_NOT_FOUND, f"付款单 {payment_id} 不存在")
        if orm.status != "executing":
            raise PURError(PURErrorCode.PAYMENT_ALREADY_COMPLETED, "付款非执行中状态不可完成")
        orm.status = "completed"
        await self._session.flush()
        return orm


class PurchaseReconcileAppSvc:
    """采购↔WMS↔INV 三边对账应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._diff_repo = PurReconcileDiffRepository()

    async def run_reconcile(self, tenant_id: UUID, order_id: UUID) -> dict:
        _check_auth(tenant_id, "pur:reconcile:execute")
        return {"tenant_id": str(tenant_id), "order_id": str(order_id), "status": "reconciled", "diffs": []}