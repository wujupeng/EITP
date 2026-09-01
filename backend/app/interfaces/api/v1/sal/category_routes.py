"""客户分类管理路由 - design 2.3.2.1。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.sal_app_services import CustomerCategoryAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.sal import CreateCategoryRequest

router = APIRouter(prefix="/sal/customer-categories", tags=["sal-category"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


@router.post("")
@require_permission("sal:category:manage")
async def create_category(req: CreateCategoryRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = CustomerCategoryAppSvc(session)
    orm = await svc.create_category(tenant_id, req.category_code, req.category_name, req.description)
    await session.commit()
    return {"category_id": str(orm.category_id), "category_code": orm.category_code, "status": orm.status}


@router.get("")
@require_permission("sal:category:manage")
async def list_categories(
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = CustomerCategoryAppSvc(session)
    items = await svc.list_categories(tenant_id, offset, limit)
    return [
        {"category_id": str(c.category_id), "category_code": c.category_code,
         "category_name": c.category_name, "status": c.status}
        for c in items
    ]