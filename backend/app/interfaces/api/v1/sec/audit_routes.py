"""审计查询路由。"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.interfaces.middleware.permission_interceptor import require_permission

router = APIRouter(prefix="/sec/audit", tags=["sec-audit"])


@router.get("")
@require_permission("sec:audit:view")
async def list_audit(
    batch_id: str | None = Query(None),
    action_type: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
) -> dict:
    return {"records": [], "total": 0}