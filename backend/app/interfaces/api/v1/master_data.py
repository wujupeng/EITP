"""主数据接口 - /api/v1/master-data/*。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.masterdata.master_data_app_svc import MasterDataAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.tenant_context import TenantContext
from app.interfaces.schemas.master_data import (
    CompanyOverrideResponse,
    CreateSkuRequest,
    EffectiveSkuResponse,
    MasterDataSkuResponse,
    SetCompanyOverrideRequest,
    SetWarehouseOverrideRequest,
    UpdateBaseRequest,
    WarehouseOverrideResponse,
)

router = APIRouter(prefix="/master-data", tags=["master-data"])


def _require_context() -> TenantContext:
    ctx = TenantContext.current()
    if ctx is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="无租户上下文")
    return ctx


@router.post("/sku", response_model=MasterDataSkuResponse, status_code=201)
async def create_sku(
    req: CreateSkuRequest,
    session: AsyncSession = Depends(get_db_session),
) -> MasterDataSkuResponse:
    """创建集团主数据基准（design 2.2.2.6）。"""
    _require_context()
    svc = MasterDataAppSvc(session)
    base = await svc.create_base(
        enterprise_id=req.enterprise_id,
        sku_code=req.sku_code,
        base_attrs=req.base_attrs,
    )
    return MasterDataSkuResponse(
        id=base.id.value,
        enterprise_id=base.enterprise_id,
        sku_code=base.sku_code,
        base_attrs=base.base_attrs,
        version=base.version,
    )


@router.put("/sku/{sku_id}", response_model=MasterDataSkuResponse)
async def update_sku(
    sku_id: UUID,
    req: UpdateBaseRequest,
    session: AsyncSession = Depends(get_db_session),
) -> MasterDataSkuResponse:
    """更新集团主数据基准（仅集团管理员）。"""
    _require_context()
    svc = MasterDataAppSvc(session)
    base = await svc.update_base(
        master_data_id=sku_id,
        new_attrs=req.base_attrs,
        expected_version=req.expected_version,
        is_group_admin=req.is_group_admin,
    )
    return MasterDataSkuResponse(
        id=base.id.value,
        enterprise_id=base.enterprise_id,
        sku_code=base.sku_code,
        base_attrs=base.base_attrs,
        version=base.version,
    )


@router.put(
    "/sku/{sku_id}/company-override",
    response_model=CompanyOverrideResponse,
)
async def set_company_override(
    sku_id: UUID,
    req: SetCompanyOverrideRequest,
    session: AsyncSession = Depends(get_db_session),
) -> CompanyOverrideResponse:
    """设置公司级属性覆盖。"""
    _require_context()
    svc = MasterDataAppSvc(session)
    override = await svc.set_company_override(
        master_data_id=sku_id,
        organization_id=req.organization_id,
        company_attrs=req.company_attrs,
        actor_org_id=req.actor_org_id,
    )
    return CompanyOverrideResponse(
        override_id=override.override_id,
        master_data_id=override.master_data_id,
        organization_id=override.organization_id,
        company_attrs=override.company_attrs,
        version=override.version,
    )


@router.put(
    "/sku/{sku_id}/warehouse-override",
    response_model=WarehouseOverrideResponse,
)
async def set_warehouse_override(
    sku_id: UUID,
    req: SetWarehouseOverrideRequest,
    session: AsyncSession = Depends(get_db_session),
) -> WarehouseOverrideResponse:
    """设置仓库级属性覆盖。"""
    _require_context()
    svc = MasterDataAppSvc(session)
    override = await svc.set_warehouse_override(
        master_data_id=sku_id,
        warehouse_id=req.warehouse_id,
        warehouse_attrs=req.warehouse_attrs,
    )
    return WarehouseOverrideResponse(
        override_id=override.override_id,
        master_data_id=override.master_data_id,
        warehouse_id=override.warehouse_id,
        warehouse_attrs=override.warehouse_attrs,
        version=override.version,
    )


@router.get("/sku/{sku_id}/effective", response_model=EffectiveSkuResponse)
async def get_effective_sku(
    sku_id: UUID,
    organization_id: UUID | None = Query(default=None),
    warehouse_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> EffectiveSkuResponse:
    """查询三层合并后的最终生效属性。"""
    _require_context()
    svc = MasterDataAppSvc(session)
    effective = await svc.get_effective_attrs(
        master_data_id=sku_id,
        organization_id=organization_id,
        warehouse_id=warehouse_id,
    )
    return EffectiveSkuResponse(
        master_data_id=sku_id,
        organization_id=organization_id,
        warehouse_id=warehouse_id,
        effective_attrs=effective,
        base_version=0,
    )