"""报告查询与证据下钻路由。"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.interfaces.middleware.permission_interceptor import require_permission

router = APIRouter(prefix="/sec/reports", tags=["sec-report"])


@router.get("")
@require_permission("sec:report:view")
async def list_reports(
    batch_id: str | None = Query(None),
    conclusion: str | None = Query(None),
    fmt: str = Query("json"),
    limit: int = Query(20, le=100),
) -> dict:
    return {"reports": [], "total": 0}


@router.get("/{report_id}")
@require_permission("sec:report:view")
async def get_report(report_id: str, fmt: str = Query("json")) -> dict:
    return {"report_id": report_id, "format": fmt}


@router.get("/{report_id}/items/{item_id}/evidence")
@require_permission("sec:report:evidence:view")
async def get_evidence(report_id: str, item_id: str) -> dict:
    return {"report_id": report_id, "item_id": item_id, "evidence": {}}