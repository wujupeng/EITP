"""单据管理路由。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.inv.inv_app_svc import DocumentAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.security_context import SecurityContext

router = APIRouter(prefix="/inv/documents", tags=["inv-document"])


@router.get("", response_model=list[dict])
async def list_documents(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    svc = DocumentAppSvc(session)
    return await svc.list_documents(tenant_id, limit, offset)
