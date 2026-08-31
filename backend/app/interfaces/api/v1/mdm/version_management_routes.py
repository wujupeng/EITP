"""版本管理路由 - /api/v1/group/versions, /api/v1/tenant/mdm/versions。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.governance.version_management_app_svc import (
    VersionManagementAppSvc,
)
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.schemas.mdm import (
    VersionCompareRequest,
    VersionCompareResponse,
    VersionResponse,
)

router = APIRouter(prefix="/group/versions", tags=["mdm-version-group"])


@router.get("", response_model=list[dict])
@require_permission("mdm:version:query")
async def list_versions(
    entity_type: str = Query(...),
    entity_id: UUID = Query(...),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    svc = VersionManagementAppSvc(session)
    orms = await svc.list_versions(entity_type, entity_id)
    return [
        {
            "version_id": str(orm.version_id),
            "tenant_id": str(orm.tenant_id) if orm.tenant_id else None,
            "entity_type": orm.entity_type,
            "entity_id": str(orm.entity_id),
            "version_number": orm.version_number,
            "snapshot_before": orm.snapshot_before,
            "snapshot_after": orm.snapshot_after,
            "change_type": orm.change_type,
            "operated_by": str(orm.operated_by),
            "reason": orm.reason,
            "operated_at": orm.operated_at.isoformat(),
        }
        for orm in orms
    ]


@router.post(":compare", response_model=VersionCompareResponse)
@require_permission("mdm:version:compare")
async def compare_versions(
    req: VersionCompareRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = VersionManagementAppSvc(session)
    return await svc.compare_versions(
        entity_type=req.entity_type,
        entity_id=req.entity_id,
        version_a=req.version_a,
        version_b=req.version_b,
    )


@router.get("/{entity_type}/{entity_id}/{version_number}", response_model=dict)
@require_permission("mdm:version:query")
async def get_version(
    entity_type: str,
    entity_id: UUID,
    version_number: int,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = VersionManagementAppSvc(session)
    orms = await svc.list_versions(entity_type, entity_id)
    for orm in orms:
        if orm.version_number == version_number:
            return {
                "version_id": str(orm.version_id),
                "tenant_id": str(orm.tenant_id) if orm.tenant_id else None,
                "entity_type": orm.entity_type,
                "entity_id": str(orm.entity_id),
                "version_number": orm.version_number,
                "snapshot_before": orm.snapshot_before,
                "snapshot_after": orm.snapshot_after,
                "change_type": orm.change_type,
                "operated_by": str(orm.operated_by),
                "reason": orm.reason,
                "operated_at": orm.operated_at.isoformat(),
            }
    return {}


enterprise_router = APIRouter(prefix="/tenant/mdm/versions", tags=["mdm-version-enterprise"])


@enterprise_router.get("", response_model=list[dict])
@require_permission("mdm:version:query")
async def list_enterprise_versions(
    entity_type: str = Query(...),
    entity_id: UUID = Query(...),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    svc = VersionManagementAppSvc(session)
    orms = await svc.list_versions(entity_type, entity_id)
    return [
        {
            "version_id": str(orm.version_id),
            "tenant_id": str(orm.tenant_id) if orm.tenant_id else None,
            "entity_type": orm.entity_type,
            "entity_id": str(orm.entity_id),
            "version_number": orm.version_number,
            "snapshot_before": orm.snapshot_before,
            "snapshot_after": orm.snapshot_after,
            "change_type": orm.change_type,
            "operated_by": str(orm.operated_by),
            "reason": orm.reason,
            "operated_at": orm.operated_at.isoformat(),
        }
        for orm in orms
    ]


router.include_router(enterprise_router)
