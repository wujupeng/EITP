"""移库作业路由。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.warehouse.transfer_app_svc import TransferAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.wms import TransferApproveRequest, TransferExecuteRequest

router = APIRouter(prefix="/wms/transfer", tags=["wms-transfer"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


def _get_user_id() -> UUID:
    ctx = SecurityContext.current()
    return ctx.user.user_id if ctx and ctx.user else UUID(int=0)


@router.post("/orders/{transfer_id}/submit")
@require_permission("wms:transfer:execute")
async def submit_transfer(
    transfer_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = TransferAppSvc(session)
    result = await svc.submit_for_approval(tenant_id, transfer_id)
    await session.commit()
    return result


@router.post("/orders/{transfer_id}/approve")
@require_permission("wms:transfer:approve")
async def approve_transfer(
    transfer_id: UUID,
    req: TransferApproveRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    svc = TransferAppSvc(session)
    result = await svc.approve(tenant_id, transfer_id, user_id, req.opinion)
    await session.commit()
    return result


@router.post("/orders/{transfer_id}/execute")
@require_permission("wms:transfer:execute")
async def execute_transfer(
    transfer_id: UUID,
    req: TransferExecuteRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    svc = TransferAppSvc(session)
    result = await svc.execute_transfer(
        tenant_id, transfer_id, req.line_id, req.transfer_quantity, user_id
    )
    await session.commit()
    return result
