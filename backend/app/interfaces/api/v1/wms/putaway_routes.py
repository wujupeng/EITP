"""上架作业路由。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.warehouse.putaway_app_svc import PutawayAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.wms import PutawayExecuteRequest

router = APIRouter(prefix="/wms/putaway", tags=["wms-putaway"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


def _get_user_id() -> UUID:
    ctx = SecurityContext.current()
    return ctx.user.user_id if ctx and ctx.user else UUID(int=0)


@router.post("/tasks/{putaway_id}/execute")
@require_permission("wms:putaway:execute")
async def execute_putaway(
    putaway_id: UUID,
    req: PutawayExecuteRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    svc = PutawayAppSvc(session)
    result = await svc.execute_putaway(
        tenant_id, putaway_id, req.target_location_id, req.putaway_quantity, user_id
    )
    await session.commit()
    return result
