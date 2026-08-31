"""企业商品路由 - /api/v1/tenant/mdm/enterprise-products。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.enterprise_product.enterprise_product_app_svc import (
    EnterpriseProductAppSvc,
)
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.mdm import (
    EnterpriseProductResponse,
    ReferenceGroupProductRequest,
)

router = APIRouter(prefix="/tenant/mdm/enterprise-products", tags=["mdm-enterprise-product"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


@router.post(":reference", response_model=EnterpriseProductResponse, status_code=201)
@require_permission("mdm:enterprise_product:manage")
async def reference_group_product(
    req: ReferenceGroupProductRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = EnterpriseProductAppSvc(session)
    agg = await svc.reference_group_product(
        tenant_id=tenant_id,
        group_product_id=req.group_product_id,
        enterprise_product_code=req.enterprise_product_code,
        enterprise_product_name=req.enterprise_product_name,
        enterprise_category_id=req.enterprise_category_id,
    )
    await session.commit()
    return {
        "enterprise_product_id": agg.id.value,
        "tenant_id": agg.tenant_id,
        "group_product_id": agg.group_product_id,
        "enterprise_product_code": agg.enterprise_product_code,
        "enterprise_product_name": agg.enterprise_product_name,
        "enterprise_category_id": agg.enterprise_category_id,
        "reference_status": agg.reference_status.value,
        "published_version": agg.published_version,
    }


@router.post("/{enterprise_product_id}:release-reference", response_model=dict)
@require_permission("mdm:enterprise_product:manage")
async def release_reference(
    enterprise_product_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = EnterpriseProductAppSvc(session)
    agg = await svc.release_reference(tenant_id, enterprise_product_id)
    await session.commit()
    return {
        "enterprise_product_id": agg.id.value,
        "reference_status": agg.reference_status.value,
    }


@router.get("", response_model=list[dict])
@require_permission("mdm:enterprise_product:manage")
async def list_enterprise_products(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = EnterpriseProductAppSvc(session)
    orms = await svc.list_enterprise_products(tenant_id, offset=offset, limit=limit)
    return [
        {
            "enterprise_product_id": str(orm.enterprise_product_id),
            "tenant_id": str(orm.tenant_id),
            "group_product_id": str(orm.group_product_id),
            "enterprise_product_code": orm.enterprise_product_code,
            "enterprise_product_name": orm.enterprise_product_name,
            "enterprise_category_id": str(orm.enterprise_category_id) if orm.enterprise_category_id else None,
            "reference_status": orm.reference_status,
            "published_version": orm.published_version,
        }
        for orm in orms
    ]


@router.get("/{enterprise_product_id}", response_model=dict)
@require_permission("mdm:enterprise_product:manage")
async def get_enterprise_product(
    enterprise_product_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = EnterpriseProductAppSvc(session)
    orm = await svc.get_enterprise_product(tenant_id, enterprise_product_id)
    if orm is None:
        return {}
    return {
        "enterprise_product_id": str(orm.enterprise_product_id),
        "tenant_id": str(orm.tenant_id),
        "group_product_id": str(orm.group_product_id),
        "enterprise_product_code": orm.enterprise_product_code,
        "enterprise_product_name": orm.enterprise_product_name,
        "enterprise_category_id": str(orm.enterprise_category_id) if orm.enterprise_category_id else None,
        "reference_status": orm.reference_status,
        "published_version": orm.published_version,
    }
