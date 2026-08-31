"""库存查询路由 - 查询余额和账本。"""

from __future__ import annotations

import time
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.inv.inv_app_svc import InventoryAppSvc
from app.infrastructure.db.session import get_db_session
from app.infrastructure.observability.metrics import record_balance_query
from app.interfaces.middleware.security_context import SecurityContext

router = APIRouter(prefix="/inv/inventory/query", tags=["inv-inventory-query"])


@router.get("/balance", response_model=list[dict])
async def query_balance(
    sku_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    _start = time.monotonic()
    svc = InventoryAppSvc(session)
    result = await svc.query_balance(tenant_id, sku_id, warehouse_id)
    _duration_ms = (time.monotonic() - _start) * 1000
    record_balance_query(
        str(tenant_id) if tenant_id else "",
        str(warehouse_id) if warehouse_id else "",
        _duration_ms,
    )
    return result


@router.get("/ledger", response_model=list[dict])
async def query_ledger(
    sku_id: UUID,
    warehouse_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    svc = InventoryAppSvc(session)
    return await svc.query_ledger(tenant_id, sku_id, warehouse_id, limit)
