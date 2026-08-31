"""收货作业路由。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.warehouse.receiving_app_svc import ReceivingAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.wms import ReceivingExecuteRequest

router = APIRouter(prefix="/wms/receiving", tags=["wms-receiving"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


def _get_user_id() -> UUID:
    ctx = SecurityContext.current()
    return ctx.user.user_id if ctx and ctx.user else UUID(int=0)


@router.post("/orders/{receiving_id}/execute")
@require_permission("wms:receiving:execute")
async def execute_receiving(
    receiving_id: UUID,
    req: ReceivingExecuteRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    svc = ReceivingAppSvc(session)
    result = await svc.execute_receiving(
        tenant_id, receiving_id, req.line_id, req.received_quantity,
        req.location_id, user_id,
    )
    await session.commit()
    return result
