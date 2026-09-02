"""封版报告 API 路由 - 3 个接口。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query
from structlog import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/rel/reports", tags=["REL-Report"])


@router.post("/{release_id}/assemble")
async def assemble_report(release_id: UUID, executed_by: str = Query(...)) -> dict:
    logger.info("assemble_report", release_id=str(release_id))
    return {"release_id": str(release_id), "report": "pending"}


@router.get("/{release_id}")
async def get_report(release_id: UUID) -> dict:
    return {"release_id": str(release_id), "report": "NOT_FOUND"}


@router.get("/{release_id}/verdict")
async def get_verdict(release_id: UUID) -> dict:
    return {"release_id": str(release_id), "verdict": "PENDING"}