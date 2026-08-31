"""负库存策略路由 - /api/v1/tenant/mdm/config/negative-inventory-policy, /api/v1/tenant/mdm/audit/negative-inventory-policy。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.governance.negative_policy_app_svc import NegativePolicyAppSvc
from app.domain.governance.aggregates.negative_inventory_policy_audit_aggregate import (
    NegativePolicyMode,
)
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.mdm import (
    NegativePolicyAuditResponse,
    NegativePolicyConfigRequest,
    NegativePolicyConfigResponse,
)

router = APIRouter(prefix="/tenant/mdm", tags=["mdm-negative-policy"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


@router.get("/config/negative-inventory-policy", response_model=NegativePolicyConfigResponse)
@require_permission("mdm:negative_policy:config")
async def get_negative_policy(
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = NegativePolicyAppSvc(session)
    policy = await svc.get_current_policy(tenant_id)
    return {"tenant_id": tenant_id, "policy_mode": policy.value}


@router.put("/config/negative-inventory-policy", response_model=NegativePolicyAuditResponse)
@require_permission("mdm:negative_policy:config")
async def change_negative_policy(
    req: NegativePolicyConfigRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = NegativePolicyAppSvc(session)
    mode_map = {
        "strict": NegativePolicyMode.STRICT,
        "allow": NegativePolicyMode.ALLOW,
        "warning": NegativePolicyMode.WARNING,
        "approval": NegativePolicyMode.APPROVAL,
    }
    audit_agg = await svc.change_policy(
        tenant_id=tenant_id,
        new_policy=mode_map[req.policy_mode],
        reason=req.reason,
    )
    await session.commit()
    return {
        "audit_id": audit_agg.audit_id,
        "tenant_id": audit_agg.tenant_id,
        "policy_before": audit_agg.policy_before.value,
        "policy_after": audit_agg.policy_after.value,
        "operated_by": audit_agg.operated_by,
        "reason": audit_agg.reason,
        "operated_at": audit_agg.operated_at,
    }


@router.get("/audit/negative-inventory-policy", response_model=list[dict])
@require_permission("mdm:negative_policy:audit:query")
async def list_negative_policy_audit(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = NegativePolicyAppSvc(session)
    orms = await svc.list_audit_history(tenant_id, offset=offset, limit=limit)
    return [
        {
            "audit_id": str(orm.audit_id),
            "tenant_id": str(orm.tenant_id),
            "policy_before": orm.policy_before,
            "policy_after": orm.policy_after,
            "operated_by": str(orm.operated_by),
            "reason": orm.reason,
            "operated_at": orm.operated_at.isoformat(),
        }
        for orm in orms
    ]
