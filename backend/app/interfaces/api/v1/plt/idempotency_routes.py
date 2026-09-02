"""幂等体系 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Query
from structlog import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/plt/idempotency", tags=["PLT-Idempotency"])


@router.get("/records")
async def list_idempotency_records(
    tenant_id: str = Query(...),
    limit: int = Query(100, ge=1, le=1000),
) -> dict:
    return {"items": [], "total": 0}


@router.delete("/records/{idempotency_key}")
async def delete_idempotency_record(idempotency_key: str) -> dict:
    logger.info("idempotency_delete", key=idempotency_key)
    return {"deleted": True, "key": idempotency_key}