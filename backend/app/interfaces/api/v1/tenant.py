"""平台运营租户管理接口 - /api/v1/platform/tenants。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.tenant.tenant_app_svc import TenantAppSvc
from app.domain.tenant.tenant_state import DataPlacement
from app.infrastructure.db.session import get_db_session
from app.interfaces.schemas.tenant import (
    ProvisionTenantRequest,
    StatusTransitionRequest,
    TenantResponse,
)

router = APIRouter(prefix="/platform/tenants", tags=["platform-tenant"])


@router.post("", response_model=TenantResponse, status_code=201)
async def provision_tenant(
    req: ProvisionTenantRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TenantResponse:
    """开通新租户。"""
    svc = TenantAppSvc(session)
    placement = DataPlacement(req.data_placement)
    tenant = await svc.provision(
        enterprise_name=req.enterprise_name,
        idempotency_key=req.idempotency_key,
        data_placement=placement,
    )
    return TenantResponse(
        id=tenant.id.value,
        enterprise_name=tenant.enterprise_name,
        status=tenant.status.value,
        data_placement=tenant.data_placement.value,
        version=tenant.version,
        idempotency_key=tenant.idempotency_key,
    )


@router.get("", response_model=list[TenantResponse])
async def list_tenants(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[TenantResponse]:
    """列出所有租户。"""
    svc = TenantAppSvc(session)
    tenants = await svc.list_tenants(offset, limit)
    return [
        TenantResponse(
            id=t.id.value,
            enterprise_name=t.enterprise_name,
            status=t.status.value,
            data_placement=t.data_placement.value,
            version=t.version,
            idempotency_key=t.idempotency_key,
        )
        for t in tenants
    ]


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> TenantResponse:
    """查询单个租户。"""
    svc = TenantAppSvc(session)
    tenant = await svc.get_tenant(tenant_id)
    if tenant is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="租户不存在")
    return TenantResponse(
        id=tenant.id.value,
        enterprise_name=tenant.enterprise_name,
        status=tenant.status.value,
        data_placement=tenant.data_placement.value,
        version=tenant.version,
        idempotency_key=tenant.idempotency_key,
    )


@router.post("/{tenant_id}/status", response_model=TenantResponse)
async def transition_status(
    tenant_id: UUID,
    req: StatusTransitionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TenantResponse:
    """租户状态流转。"""
    svc = TenantAppSvc(session)

    if req.action == "provision":
        tenant = await svc.complete_provision(tenant_id)
    elif req.action == "disable":
        tenant = await svc.disable(tenant_id)
    elif req.action == "enable":
        tenant = await svc.enable(tenant_id)
    elif req.action == "deprovision":
        tenant = await svc.deprovision(tenant_id, req.confirm_token)
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"未知动作: {req.action}")

    return TenantResponse(
        id=tenant.id.value,
        enterprise_name=tenant.enterprise_name,
        status=tenant.status.value,
        data_placement=tenant.data_placement.value,
        version=tenant.version,
        idempotency_key=tenant.idempotency_key,
    )