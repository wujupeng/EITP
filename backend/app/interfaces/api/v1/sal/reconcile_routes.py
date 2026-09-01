"""对账路由 - design 2.3.2.7，销售↔WMS↔INV 三边对账。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.sal_app_services import SalReconcileAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.sal import ReconcileRepairRequest, ReconcileRunRequest

router = APIRouter(prefix="/sal/reconcile", tags=["sal-reconcile"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


@router.post("/run")
@require_permission("sal:reconcile:execute")
async def run_reconcile(req: ReconcileRunRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalReconcileAppSvc(session)
    result = await svc.run_reconcile(tenant_id, req.order_id)
    await session.commit()
    return result


@router.get("/diffs")
@require_permission("sal:reconcile:execute")
async def list_diffs(
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = SalReconcileAppSvc(session)
    return await svc.list_diffs(tenant_id, offset, limit)


@router.post("/repair")
@require_permission("sal:reconcile:execute")
async def repair_diff(req: ReconcileRepairRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalReconcileAppSvc(session)
    result = await svc.repair(tenant_id, req.shipment_id, req.repair_note)
    await session.commit()
    return result