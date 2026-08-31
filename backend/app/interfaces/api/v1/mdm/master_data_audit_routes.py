"""主数据审计路由 - /api/v1/tenant/mdm/audit/master-data。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.governance.master_data_audit_app_svc import (
    MasterDataAuditAppSvc,
)
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext

router = APIRouter(prefix="/tenant/mdm/audit", tags=["mdm-master-data-audit"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


@router.get("/master-data", response_model=list[dict])
@require_permission("mdm:master_data:query")
async def list_master_data_audit(
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
    action: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = MasterDataAuditAppSvc(session)

    if entity_type and entity_id:
        orms = await svc.list_by_entity(entity_type, entity_id, offset=offset, limit=limit)
    else:
        orms = await svc.list_by_tenant(tenant_id, offset=offset, limit=limit)

    results = []
    for orm in orms:
        entry = {
            "audit_id": str(orm.audit_id),
            "tenant_id": str(orm.tenant_id) if orm.tenant_id else None,
            "action": orm.action,
            "entity_type": orm.entity_type,
            "entity_id": orm.entity_id,
            "version_number": orm.version_number,
            "old_value": orm.old_value,
            "new_value": orm.new_value,
            "operated_by": str(orm.operated_by) if orm.operated_by else None,
            "operated_at": orm.operated_at.isoformat(),
            "reason": orm.reason,
            "ip_address": orm.ip_address,
        }
        if action is None or orm.action == action:
            results.append(entry)
    return results
