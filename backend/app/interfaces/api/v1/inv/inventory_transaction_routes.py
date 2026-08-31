"""库存事务路由 - 执行库存事务（幂等）。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.inv.inv_app_svc import InventoryAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.inv import InventoryTransactionRequest, InventoryTransactionResponse

router = APIRouter(prefix="/inv/inventory/transactions", tags=["inv-inventory-tx"])


@router.post("", response_model=dict, status_code=201)
async def execute_transaction(
    req: InventoryTransactionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    user_id = ctx.user.user_id if ctx else None
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    svc = InventoryAppSvc(session)
    return await svc.execute_transaction(
        tenant_id=tenant_id,
        sku_id=req.sku_id,
        warehouse_id=req.warehouse_id,
        transaction_type=req.transaction_type,
        quantity=req.quantity,
        idempotency_key=req.idempotency_key,
        operated_by=user_id,
        correlation_id=req.correlation_id,
        document_id=req.document_id,
        document_type=req.document_type,
        organization_id=req.organization_id,
        site_id=req.site_id,
        location_id=req.location_id,
        unit_cost=req.unit_cost,
        reason=req.reason,
    )
