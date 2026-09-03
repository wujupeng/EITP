"""数据一致性 API 路由 - Outbox + Saga。"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from structlog import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/plt/consistency", tags=["PLT-Consistency"])


@router.get("/outbox/events")
async def list_outbox_events(
    status: str = Query("PENDING"),
    limit: int = Query(100, ge=1, le=1000),
) -> dict:
    return {"items": [], "total": 0, "status": status}


@router.post("/outbox/events/{event_id}/retry")
async def retry_outbox_event(event_id: str) -> dict:
    logger.info("outbox_retry", event_id=event_id)
    return {"event_id": event_id, "status": "RETRYING"}


@router.get("/saga/instances")
async def list_saga_instances(
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
) -> dict:
    return {"items": [], "total": 0}


@router.get("/saga/instances/{saga_id}")
async def get_saga_instance(saga_id: str) -> dict:
    return {"saga_id": saga_id, "status": "RUNNING"}


@router.post("/saga/instances/{saga_id}/compensate")
async def compensate_saga(saga_id: str) -> dict:
    logger.info("saga_compensate", saga_id=saga_id)
    return {"saga_id": saga_id, "status": "COMPENSATING"}