"""BIZ-OPS 操作路由 - 审批操作 + 税务计算 + 库存策略查询 API。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.biz_ops.strategy_config_app_svc import StrategyConfigAppSvc
from app.application.biz_ops.inventory_orchestrator import InventoryOrchestrator
from app.application.biz_ops.purchase_orchestrator import PurchaseOrchestrator
from app.application.biz_ops.sales_orchestrator import SalesOrchestrator
from app.application.biz_ops.warehouse_orchestrator import WarehouseOrchestrator
from app.domain.biz_ops.services.approval_orchestrator import ApprovalOrchestrator
from app.infrastructure.biz_ops.repositories.approval_flow_repository import ApprovalFlowRepository
from app.infrastructure.db.session import get_db_session
from app.interfaces.api.v1.biz_ops.schemas.approval_flow_schema import (
    ApprovalActionRequest,
    ApprovalActionResponse,
)
from app.interfaces.api.v1.biz_ops.schemas.operation_schemas import (
    InventoryAdjustRequest,
    InventoryCountRequest,
    InventoryOutboundRequest,
    InventoryTransferRequest,
    OperationRequest,
    PurchaseOrderCreateRequest,
    PurchaseReceiptRequest,
    PurchaseReturnRequest,
    SalesOrderCreateRequest,
    SalesReturnRequest,
    SalesShipmentRequest,
    WarehouseTaskRequest,
)
from app.interfaces.api.v1.biz_ops.schemas.tax_config_schema import TaxCalculationRequest
from app.interfaces.middleware.error_handler import BizOpsError, BizOpsErrorCode
from app.interfaces.middleware.security_context import SecurityContext

router = APIRouter(prefix="/biz-ops/operations", tags=["biz-ops-operations"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    if ctx is None:
        raise BizOpsError(BizOpsErrorCode.INTERNAL_ERROR, "安全上下文缺失")
    tid = ctx.tenant.tenant_id
    return UUID(str(tid)) if isinstance(tid, str) else tid


def _get_user_id() -> UUID:
    ctx = SecurityContext.current()
    if ctx is None:
        raise BizOpsError(BizOpsErrorCode.INTERNAL_ERROR, "安全上下文缺失")
    uid = ctx.user.user_id
    return UUID(str(uid)) if isinstance(uid, str) else uid


@router.post("/approvals/{approval_id}/approve")
async def approve(approval_id: UUID, req: ApprovalActionRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    return {"approval_id": str(approval_id), "action": "approve", "status": "processed"}


@router.post("/approvals/{approval_id}/reject")
async def reject(approval_id: UUID, req: ApprovalActionRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    return {"approval_id": str(approval_id), "action": "reject", "status": "rejected"}


@router.post("/approvals/{approval_id}/return")
async def return_approval(approval_id: UUID, req: ApprovalActionRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    return {"approval_id": str(approval_id), "action": "return", "status": "returned"}


@router.post("/approvals/{approval_id}/add-sign")
async def add_sign(approval_id: UUID, req: ApprovalActionRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    return {"approval_id": str(approval_id), "action": "add_sign", "status": "add_sign"}


@router.post("/approvals/{approval_id}/transfer")
async def transfer(approval_id: UUID, req: ApprovalActionRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    return {"approval_id": str(approval_id), "action": "transfer", "status": "transfer"}


@router.post("/approvals/{approval_id}/delegate")
async def delegate(approval_id: UUID, req: ApprovalActionRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    return {"approval_id": str(approval_id), "action": "delegate", "status": "delegate"}


@router.get("/approvals/pending")
async def list_pending_approvals(session: AsyncSession = Depends(get_db_session)) -> list[dict]:
    return []


# ==================== 税务计算 API ====================

@router.post("/tax/calculate")
async def calculate_tax(
    req: TaxCalculationRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = StrategyConfigAppSvc(session)
    return await svc.calculate_tax(tenant_id, req.model_dump())


# ==================== 库存策略查询 API ====================

@router.get("/inventory/strategies/alerts")
async def list_inventory_alerts(session: AsyncSession = Depends(get_db_session)) -> list[dict]:
    return []


@router.get("/inventory/strategies/replenish-suggestions")
async def list_replenish_suggestions(session: AsyncSession = Depends(get_db_session)) -> list[dict]:
    return []


# ==================== 采购操作编排 API (5) ====================

@router.post("/purchase/orders")
async def create_purchase_order(req: PurchaseOrderCreateRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id, user_id = _get_tenant_id(), _get_user_id()
    return await PurchaseOrchestrator(session).create_order(tenant_id, user_id, req.model_dump(), req.idempotency_key or "")

@router.post("/purchase/orders/submit")
async def submit_purchase_order(req: OperationRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id, user_id = _get_tenant_id(), _get_user_id()
    return await PurchaseOrchestrator(session).submit_order(tenant_id, user_id, req.model_dump(), req.idempotency_key or "")

@router.post("/purchase/orders/approve")
async def approve_purchase_order(req: OperationRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id, user_id = _get_tenant_id(), _get_user_id()
    return await PurchaseOrchestrator(session).approve_order(tenant_id, user_id, req.model_dump(), req.idempotency_key or "")

@router.post("/purchase/receipts")
async def create_purchase_receipt(req: PurchaseReceiptRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id, user_id = _get_tenant_id(), _get_user_id()
    return await PurchaseOrchestrator(session).receipt(tenant_id, user_id, req.model_dump(), req.idempotency_key or "")

@router.post("/purchase/returns")
async def create_purchase_return(req: PurchaseReturnRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id, user_id = _get_tenant_id(), _get_user_id()
    return await PurchaseOrchestrator(session).return_goods(tenant_id, user_id, req.model_dump(), req.idempotency_key or "")


# ==================== 销售操作编排 API (4) ====================

@router.post("/sales/orders")
async def create_sales_order(req: SalesOrderCreateRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id, user_id = _get_tenant_id(), _get_user_id()
    return await SalesOrchestrator(session).create_order(tenant_id, user_id, req.model_dump(), req.idempotency_key or "")

@router.post("/sales/orders/submit")
async def submit_sales_order(req: SalesOrderCreateRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id, user_id = _get_tenant_id(), _get_user_id()
    return await SalesOrchestrator(session).submit_order(tenant_id, user_id, req.model_dump(), req.idempotency_key or "")

@router.post("/sales/shipments")
async def create_sales_shipment(req: SalesShipmentRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id, user_id = _get_tenant_id(), _get_user_id()
    return await SalesOrchestrator(session).shipment(tenant_id, user_id, req.model_dump(), req.idempotency_key or "")

@router.post("/sales/returns")
async def create_sales_return(req: SalesReturnRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id, user_id = _get_tenant_id(), _get_user_id()
    return await SalesOrchestrator(session).return_goods(tenant_id, user_id, req.model_dump(), req.idempotency_key or "")


# ==================== 库存操作编排 API (5) ====================

@router.post("/inventory/inbound")
async def inventory_inbound(req: OperationRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id, user_id = _get_tenant_id(), _get_user_id()
    return await InventoryOrchestrator(session).inbound(tenant_id, user_id, req.model_dump(), req.idempotency_key or "")

@router.post("/inventory/outbound")
async def inventory_outbound(req: InventoryOutboundRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id, user_id = _get_tenant_id(), _get_user_id()
    return await InventoryOrchestrator(session).outbound(tenant_id, user_id, req.model_dump(), req.idempotency_key or "")

@router.post("/inventory/transfers")
async def inventory_transfer(req: InventoryTransferRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id, user_id = _get_tenant_id(), _get_user_id()
    return await InventoryOrchestrator(session).transfer(tenant_id, user_id, req.model_dump(), req.idempotency_key or "")

@router.post("/inventory/counts")
async def inventory_count(req: InventoryCountRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id, user_id = _get_tenant_id(), _get_user_id()
    return await InventoryOrchestrator(session).count(tenant_id, user_id, req.model_dump(), req.idempotency_key or "")

@router.post("/inventory/adjustments")
async def inventory_adjust(req: InventoryAdjustRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id, user_id = _get_tenant_id(), _get_user_id()
    return await InventoryOrchestrator(session).adjust(tenant_id, user_id, req.model_dump(), req.idempotency_key or "")


# ==================== 仓库操作编排 API (5) ====================

@router.post("/warehouse/receiving")
async def warehouse_receiving(req: WarehouseTaskRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id, user_id = _get_tenant_id(), _get_user_id()
    return await WarehouseOrchestrator(session).receiving(tenant_id, user_id, req.model_dump(), req.idempotency_key or "")

@router.post("/warehouse/putaway")
async def warehouse_putaway(req: WarehouseTaskRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id, user_id = _get_tenant_id(), _get_user_id()
    return await WarehouseOrchestrator(session).putaway(tenant_id, user_id, req.model_dump(), req.idempotency_key or "")

@router.post("/warehouse/picking")
async def warehouse_picking(req: WarehouseTaskRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id, user_id = _get_tenant_id(), _get_user_id()
    return await WarehouseOrchestrator(session).picking(tenant_id, user_id, req.model_dump(), req.idempotency_key or "")

@router.post("/warehouse/transfers")
async def warehouse_transfer(req: WarehouseTaskRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id, user_id = _get_tenant_id(), _get_user_id()
    return await WarehouseOrchestrator(session).transfer(tenant_id, user_id, req.model_dump(), req.idempotency_key or "")

@router.post("/warehouse/shipping")
async def warehouse_shipping(req: WarehouseTaskRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id, user_id = _get_tenant_id(), _get_user_id()
    return await WarehouseOrchestrator(session).shipping(tenant_id, user_id, req.model_dump(), req.idempotency_key or "")