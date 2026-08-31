"""治理工作流路由 - /api/v1/group/governance-requests, /api/v1/tenant/mdm/governance-requests。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.governance.governance_workflow_app_svc import (
    GovernanceWorkflowAppSvc,
)
from app.domain.governance.aggregates.governance_workflow_aggregate import GovernanceLevel
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.mdm import CreateGovernanceRequest, GovernanceActionRequest

router = APIRouter(prefix="/group/governance-requests", tags=["mdm-governance-group"])


def _get_user_id() -> UUID:
    ctx = SecurityContext.current()
    return ctx.user.user_id if ctx else None


def _get_tenant_id() -> UUID | None:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


@router.post("", response_model=dict, status_code=201)
@require_permission("mdm:governance:submit")
async def create_governance_request(
    req: CreateGovernanceRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = GovernanceWorkflowAppSvc(session)
    level = GovernanceLevel.GROUP if req.governance_level == "group" else GovernanceLevel.ENTERPRISE
    agg = await svc.create_request(
        governance_level=level,
        entity_type=req.entity_type,
        target_version_id=req.entity_id,
        tenant_id=req.tenant_id,
        entity_id=req.entity_id,
    )
    await session.commit()
    return {
        "workflow_id": agg.id.value,
        "entity_type": agg.entity_type,
        "entity_id": str(agg.entity_id) if agg.entity_id else None,
        "governance_level": agg.governance_level.value,
        "state": agg.state.value,
    }


@router.post("/{request_id}:submit", response_model=dict)
@require_permission("mdm:governance:submit")
async def submit_request(
    request_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = GovernanceWorkflowAppSvc(session)
    agg = await svc.submit_request(request_id, _get_user_id())
    await session.commit()
    return {"workflow_id": agg.id.value, "state": agg.state.value}


@router.post("/{request_id}:approve", response_model=dict)
@require_permission("mdm:governance:approve")
async def approve_request(
    request_id: UUID,
    req: GovernanceActionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = GovernanceWorkflowAppSvc(session)
    agg = await svc.approve_request(request_id, _get_user_id(), req.reason)
    await session.commit()
    return {"workflow_id": agg.id.value, "state": agg.state.value}


@router.post("/{request_id}:reject", response_model=dict)
@require_permission("mdm:governance:approve")
async def reject_request(
    request_id: UUID,
    req: GovernanceActionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = GovernanceWorkflowAppSvc(session)
    agg = await svc.reject_request(request_id, _get_user_id(), req.reason)
    await session.commit()
    return {"workflow_id": agg.id.value, "state": agg.state.value}


@router.post("/{request_id}:publish", response_model=dict)
@require_permission("mdm:governance:publish")
async def publish_request(
    request_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = GovernanceWorkflowAppSvc(session)
    agg = await svc.publish_request(request_id, _get_user_id())
    await session.commit()
    return {"workflow_id": agg.id.value, "state": agg.state.value}


@router.post("/{request_id}:rollback", response_model=dict)
@require_permission("mdm:governance:rollback")
async def rollback_request(
    request_id: UUID,
    req: GovernanceActionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = GovernanceWorkflowAppSvc(session)
    agg = await svc.rollback_request(request_id, _get_user_id(), req.reason)
    await session.commit()
    return {"workflow_id": agg.id.value, "state": agg.state.value}


@router.get("", response_model=list[dict])
@require_permission("mdm:governance:query")
async def list_governance_requests(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    svc = GovernanceWorkflowAppSvc(session)
    orms = await svc.list_pending(offset=offset, limit=limit)
    return [
        {
            "workflow_id": str(orm.workflow_id),
            "entity_type": orm.entity_type,
            "entity_id": str(orm.entity_id) if orm.entity_id else None,
            "governance_level": orm.governance_level,
            "state": orm.state,
            "current_version": orm.current_version,
            "target_version": orm.target_version,
        }
        for orm in orms
    ]


enterprise_router = APIRouter(prefix="/tenant/mdm/governance-requests", tags=["mdm-governance-enterprise"])


@enterprise_router.post("", response_model=dict, status_code=201)
@require_permission("mdm:governance:submit")
async def create_enterprise_governance_request(
    req: CreateGovernanceRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = GovernanceWorkflowAppSvc(session)
    agg = await svc.create_request(
        governance_level=GovernanceLevel.ENTERPRISE,
        entity_type=req.entity_type,
        target_version_id=req.entity_id,
        tenant_id=_get_tenant_id(),
        entity_id=req.entity_id,
    )
    await session.commit()
    return {
        "workflow_id": agg.id.value,
        "entity_type": agg.entity_type,
        "entity_id": str(agg.entity_id) if agg.entity_id else None,
        "governance_level": agg.governance_level.value,
        "state": agg.state.value,
    }


@enterprise_router.get("", response_model=list[dict])
@require_permission("mdm:governance:query")
async def list_enterprise_governance_requests(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = GovernanceWorkflowAppSvc(session)
    orms = await svc.list_by_tenant(tenant_id, offset=offset, limit=limit)
    return [
        {
            "workflow_id": str(orm.workflow_id),
            "entity_type": orm.entity_type,
            "entity_id": str(orm.entity_id) if orm.entity_id else None,
            "governance_level": orm.governance_level,
            "state": orm.state,
            "current_version": orm.current_version,
            "target_version": orm.target_version,
        }
        for orm in orms
    ]


router.include_router(enterprise_router)
