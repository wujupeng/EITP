"""门禁 API 路由 - 2 个接口。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel
from structlog import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/rel/gates", tags=["REL-Gate"])


class RetryGatesRequest(BaseModel):
    gate_types: list[str]
    executed_by: str


@router.get("/{release_id}")
async def list_gate_records(release_id: UUID) -> dict:
    return {"release_id": str(release_id), "gates": []}


@router.post("/{release_id}/retry")
async def retry_gates(release_id: UUID, req: RetryGatesRequest) -> dict:
    logger.info("retry_gates", release_id=str(release_id), gate_types=req.gate_types)
    return {"release_id": str(release_id), "retried": req.gate_types, "results": []}