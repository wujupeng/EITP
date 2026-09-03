"""回滚方案 API 路由 - 3 个接口。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel
from structlog import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/rel/rollback-plans", tags=["REL-Rollback"])


class DrillRequest(BaseModel):
    drill_result: dict


@router.get("/{release_id}")
async def get_rollback_plan(release_id: UUID) -> dict:
    return {"release_id": str(release_id), "drill_status": "NOT_DRILLED"}


@router.post("/{release_id}/drill")
async def execute_drill(release_id: UUID, req: DrillRequest) -> dict:
    logger.info("execute_drill", release_id=str(release_id))
    return {"release_id": str(release_id), "drill_status": "DRILLED_PASS"}


@router.post("/{release_id}/drill-result")
async def update_drill_result(release_id: UUID, req: DrillRequest) -> dict:
    logger.info("update_drill_result", release_id=str(release_id))
    return {"release_id": str(release_id), "drill_status": "UPDATED"}