"""WMS Task 路由 - 创建/分配/领取/取消/查询。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.warehouse.wms_task_app_svc import WmsTaskAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.wms import AssignTaskRequest, CreateTaskRequest

router = APIRouter(prefix="/wms/tasks", tags=["wms-task"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


def _get_user_id() -> UUID:
    ctx = SecurityContext.current()
    return ctx.user.user_id if ctx and ctx.user else UUID(int=0)


@router.post("")
@require_permission("wms:task:manage")
async def create_task(
    req: CreateTaskRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = WmsTaskAppSvc(session)
    orm = await svc.create_task(
        tenant_id, req.task_type, req.document_id, req.document_type,
        req.priority, req.idempotency_key, req.correlation_id,
    )
    await session.commit()
    return {"task_id": str(orm.task_id), "status": orm.status}


@router.get("")
@require_permission("wms:task:query")
async def query_tasks(
    status: str | None = Query(None),
    assignee_id: UUID | None = Query(None),
    offset: int = Query(0),
    limit: int = Query(50),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = WmsTaskAppSvc(session)
    if assignee_id is not None:
        return await svc.query_tasks_by_assignee(tenant_id, assignee_id, status)
    if status is not None:
        return await svc.query_tasks_by_status(tenant_id, status, offset, limit)
    return []


@router.post("/{task_id}/assign")
@require_permission("wms:task:assign")
async def assign_task(
    task_id: UUID,
    req: AssignTaskRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    svc = WmsTaskAppSvc(session)
    result = await svc.assign_task(tenant_id, task_id, req.assignee_id, user_id)
    await session.commit()
    return result


@router.post("/{task_id}/claim")
@require_permission("wms:task:claim")
async def claim_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    svc = WmsTaskAppSvc(session)
    result = await svc.claim_task(tenant_id, task_id, user_id)
    await session.commit()
    return result


@router.post("/{task_id}/cancel")
@require_permission("wms:task:cancel")
async def cancel_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    svc = WmsTaskAppSvc(session)
    result = await svc.cancel_task(tenant_id, task_id, user_id)
    await session.commit()
    return result
