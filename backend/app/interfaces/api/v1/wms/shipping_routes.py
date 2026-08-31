"""发货作业路由。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.warehouse.shipping_app_svc import ShippingAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.wms import ShippingExecuteRequest

router = APIRouter(prefix="/wms/shipping", tags=["wms-shipping"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


def _get_user_id() -> UUID:
    ctx = SecurityContext.current()
    return ctx.user.user_id if ctx and ctx.user else UUID(int=0)


@router.post("/orders/{shipping_id}/execute")
@require_permission("wms:shipping:execute")
async def execute_shipping(
    shipping_id: UUID,
    req: ShippingExecuteRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    svc = ShippingAppSvc(session)
    result = await svc.record_logistics(
        tenant_id, shipping_id, req.logistics_no, req.logistics_company, user_id
    )
    await session.commit()
    return result


@router.post("/orders/{shipping_id}/confirm")
@require_permission("wms:shipping:execute")
async def confirm_shipping(
    shipping_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    svc = ShippingAppSvc(session)
    result = await svc.confirm_shipping(tenant_id, shipping_id, user_id)
    await session.commit()
    return result
