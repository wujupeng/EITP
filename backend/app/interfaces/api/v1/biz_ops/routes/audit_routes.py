"""BIZ-OPS 审计查询路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.biz_ops.audit_app_svc import AuditAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.error_handler import BizOpsError, BizOpsErrorCode
from app.interfaces.middleware.security_context import SecurityContext

from uuid import UUID


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    if ctx is None:
        raise BizOpsError(BizOpsErrorCode.INTERNAL_ERROR, "安全上下文缺失")
    tid = ctx.tenant.tenant_id
    return UUID(str(tid)) if isinstance(tid, str) else tid


router = APIRouter(prefix="/biz-ops/audits", tags=["biz-ops-audits"])


@router.get("/operations")
async def query_operation_audits(
    operation_type: str | None = Query(None),
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = AuditAppSvc(session)
    return await svc.query_operations(tenant_id, operation_type, entity_type, entity_id, page, page_size)


@router.get("/strategies")
async def query_strategy_audits(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = AuditAppSvc(session)
    return await svc.query_operations(tenant_id, page=page, page_size=page_size)


@router.get("/approvals")
async def query_approval_audits(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = AuditAppSvc(session)
    return await svc.query_operations(tenant_id, page=page, page_size=page_size)