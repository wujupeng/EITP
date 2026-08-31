"""拣货作业路由。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.warehouse.picking_app_svc import PickingAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.wms import PickingExecuteRequest

router = APIRouter(prefix="/wms/picking", tags=["wms-picking"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


def _get_user_id() -> UUID:
    ctx = SecurityContext.current()
    return ctx.user.user_id if ctx and ctx.user else UUID(int=0)


@router.post("/tasks/{picking_id}/execute")
@require_permission("wms:picking:execute")
async def execute_picking(
    picking_id: UUID,
    req: PickingExecuteRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    svc = PickingAppSvc(session)
    result = await svc.execute_picking(
        tenant_id, picking_id, req.line_id, req.picked_quantity, user_id
    )
    await session.commit()
    return result
