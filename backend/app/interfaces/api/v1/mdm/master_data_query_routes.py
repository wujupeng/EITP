"""主数据查询与条码定位路由 - /api/v1/tenant/mdm/master-data, /api/v1/tenant/mdm/skus:locate-by-barcode。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.master_data_query.barcode_locator import BarcodeLocator
from app.application.master_data_query.master_data_query_app_svc import (
    MasterDataQueryAppSvc,
)
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.mdm import (
    BarcodeLocateResponse,
    MasterDataQueryResponse,
)

router = APIRouter(prefix="/tenant/mdm", tags=["mdm-master-data-query"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


@router.get("/master-data:query", response_model=list[dict])
@require_permission("mdm:master_data:query")
async def query_master_data(
    enterprise_product_code: str | None = Query(None),
    group_product_id: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = MasterDataQueryAppSvc(session)
    filter_dict: dict = {"limit": limit}
    if enterprise_product_code:
        filter_dict["enterprise_product_code"] = enterprise_product_code
    if group_product_id:
        filter_dict["group_product_id"] = str(group_product_id)
    return await svc.query_by_filter(tenant_id, filter_dict)


@router.get("/master-data/{enterprise_product_id}", response_model=MasterDataQueryResponse)
@require_permission("mdm:master_data:query")
async def get_master_data(
    enterprise_product_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = MasterDataQueryAppSvc(session)
    return await svc.get_master_data(tenant_id, enterprise_product_id)


@router.get("/skus:locate-by-barcode", response_model=BarcodeLocateResponse)
@require_permission("mdm:master_data:query")
async def locate_by_barcode(
    barcode: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    locator = BarcodeLocator(session)
    return await locator.locate(tenant_id, barcode)
