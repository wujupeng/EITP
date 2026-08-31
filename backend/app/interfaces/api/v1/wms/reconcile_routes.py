"""对账作业路由。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.warehouse.reconcile_app_svc import ReconcileAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext

router = APIRouter(prefix="/wms/reconcile", tags=["wms-reconcile"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


def _get_user_id() -> UUID:
    ctx = SecurityContext.current()
    return ctx.user.user_id if ctx and ctx.user else UUID(int=0)


@router.post("/run")
@require_permission("wms:reconcile:execute")
async def run_reconcile(
    warehouse_id: UUID = Query(...),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = ReconcileAppSvc(session)
    result = await svc.run_reconcile(tenant_id, warehouse_id, inv_balance_provider=lambda *args: {})
    await session.commit()
    return result


@router.get("/diffs")
@require_permission("wms:reconcile:execute")
async def list_diffs(
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = ReconcileAppSvc(session)
    return await svc.list_open_diffs(tenant_id)


@router.post("/diffs/{diff_id}/resolve")
@require_permission("wms:reconcile:execute")
async def resolve_diff(
    diff_id: UUID,
    resolution_note: str = "",
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    svc = ReconcileAppSvc(session)
    result = await svc.resolve_diff(tenant_id, diff_id, resolution_note, user_id)
    await session.commit()
    return result
