"""采购对账路由 - 采购↔WMS↔INV 三边对账。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.purchasing.pur_app_services import PurchaseReconcileAppSvc
from app.infrastructure.db.session import get_db_session
from app.infrastructure.purchasing.repositories import PurReconcileDiffRepository
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.pur import ReconcileRepairRequest, ReconcileRunRequest

router = APIRouter(prefix="/pur/reconcile", tags=["pur-reconcile"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


@router.post("/run")
@require_permission("pur:reconcile:execute")
async def run_reconcile(
    req: ReconcileRunRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = PurchaseReconcileAppSvc(session)
    result = await svc.run_reconcile(tenant_id, req.order_id)
    await session.commit()
    return result


@router.get("/diffs")
@require_permission("pur:reconcile:execute")
async def list_diffs(
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    repo = PurReconcileDiffRepository()
    diffs = await repo.list_open(session, tenant_id)
    return [
        {"diff_id": str(d.diff_id), "order_id": str(d.order_id), "sku_id": str(d.sku_id),
         "pur_quantity": float(d.pur_quantity), "wms_quantity": float(d.wms_quantity),
         "inv_quantity": float(d.inv_quantity), "diff_type": d.diff_type, "status": d.status}
        for d in diffs
    ]


@router.post("/repair")
@require_permission("pur:reconcile:execute")
async def repair_diff(
    req: ReconcileRepairRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    from sqlalchemy import select

    from app.infrastructure.purchasing.models import PurReconcileDiffORM
    orm = (await session.execute(
        select(PurReconcileDiffORM).where(
            PurReconcileDiffORM.tenant_id == tenant_id,
            PurReconcileDiffORM.diff_id == req.diff_id,
        )
    )).scalar_one_or_none()
    if orm is None:
        return {"error": "not_found"}
    orm.status = "repaired"
    await session.flush()
    await session.commit()
    return {"diff_id": str(orm.diff_id), "status": orm.status}