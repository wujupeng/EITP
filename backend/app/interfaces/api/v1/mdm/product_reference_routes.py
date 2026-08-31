"""商品引用路由 - /api/v1/tenant/mdm/product-references, /api/v1/group/products/{id}/references。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.enterprise_product.product_reference_app_svc import (
    ProductReferenceAppSvc,
)
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext

router = APIRouter(prefix="/tenant/mdm/product-references", tags=["mdm-product-reference"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


@router.get("", response_model=list[dict])
@require_permission("mdm:product_reference:create")
async def list_product_references(
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = ProductReferenceAppSvc(session)
    orms = await svc.list_references_by_tenant(tenant_id)
    return [
        {
            "reference_id": str(orm.reference_id),
            "tenant_id": str(orm.tenant_id),
            "group_product_id": str(orm.group_product_id),
            "enterprise_product_id": str(orm.enterprise_product_id),
            "referenced_by": str(orm.referenced_by),
            "referenced_at": orm.referenced_at.isoformat(),
            "reference_status": orm.reference_status,
            "released_by": str(orm.released_by) if orm.released_by else None,
            "released_at": orm.released_at.isoformat() if orm.released_at else None,
        }
        for orm in orms
    ]


group_ref_router = APIRouter(prefix="/group/products", tags=["mdm-product-reference-group"])


@group_ref_router.get("/{group_product_id}/references", response_model=list[dict])
@require_permission("mdm:group_product:manage")
async def list_references_by_group_product(
    group_product_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    svc = ProductReferenceAppSvc(session)
    orms = await svc.list_references_by_group_product(group_product_id)
    return [
        {
            "reference_id": str(orm.reference_id),
            "tenant_id": str(orm.tenant_id),
            "group_product_id": str(orm.group_product_id),
            "enterprise_product_id": str(orm.enterprise_product_id),
            "referenced_by": str(orm.referenced_by),
            "referenced_at": orm.referenced_at.isoformat(),
            "reference_status": orm.reference_status,
        }
        for orm in orms
    ]


router.include_router(group_ref_router)
