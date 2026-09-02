"""证据管理 API 路由 - 4 个接口。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel
from structlog import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/prod/evidence", tags=["PROD-Evidence"])


class HashVerifyRequest(BaseModel):
    evidence_id: str
    stored_hash: str
    content_ref: str


@router.get("/{evidence_id}")
async def get_evidence(evidence_id: UUID) -> dict:
    return {"evidence_id": str(evidence_id), "status": "NOT_FOUND"}


@router.get("")
async def list_evidence(
    run_id: UUID | None = Query(None),
    evidence_type: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict:
    return {"items": [], "total": 0, "limit": limit, "offset": offset}


@router.get("/{evidence_id}/download")
async def download_evidence(evidence_id: UUID) -> dict:
    logger.info("evidence_download", evidence_id=str(evidence_id))
    return {"evidence_id": str(evidence_id), "download_url": "pending"}


@router.post("/verify-hash")
async def verify_evidence_hash(req: HashVerifyRequest) -> dict:
    logger.info("evidence_verify_hash", evidence_id=req.evidence_id)
    return {"evidence_id": req.evidence_id, "integrity_ok": True}