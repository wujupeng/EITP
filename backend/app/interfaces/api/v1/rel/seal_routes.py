"""封版请求 API 路由 - 5 个接口。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel
from structlog import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/rel/seals", tags=["REL-Seal"])


class SealRequest(BaseModel):
    release_number: str
    version: str
    git_tag: str
    executed_by: str


class CoSignRequest(BaseModel):
    releaser: str
    security_officer: str


@router.post("")
async def request_seal(req: SealRequest) -> dict:
    logger.info("seal_requested", release_number=req.release_number, version=req.version)
    return {
        "release_id": "pending",
        "release_number": req.release_number,
        "version": req.version,
        "git_tag": req.git_tag,
        "seal_status": "REQUESTED",
    }


@router.post("/{release_id}/execute-gates")
async def execute_gates(release_id: UUID, executed_by: str = Query(...)) -> dict:
    logger.info("execute_gates", release_id=str(release_id))
    return {"release_id": str(release_id), "seal_status": "GATE_RUNNING"}


@router.post("/{release_id}/collect-snapshots")
async def collect_snapshots(release_id: UUID, collected_by: str = Query(...)) -> dict:
    logger.info("collect_snapshots", release_id=str(release_id))
    return {"release_id": str(release_id), "seal_status": "SNAPSHOT_COLLECTING"}


@router.post("/{release_id}/assemble-report")
async def assemble_report(release_id: UUID, executed_by: str = Query(...)) -> dict:
    logger.info("assemble_report", release_id=str(release_id))
    return {"release_id": str(release_id), "seal_status": "PENDING_CO_SIGN"}


@router.post("/{release_id}/co-sign")
async def co_sign(release_id: UUID, req: CoSignRequest) -> dict:
    logger.info("co_sign", release_id=str(release_id), releaser=req.releaser)
    return {
        "release_id": str(release_id),
        "seal_status": "SEALED",
        "verdict": "FINAL_PASS",
        "signed_by_releaser": req.releaser,
        "signed_by_security": req.security_officer,
    }


@router.get("/{release_id}")
async def get_seal(release_id: UUID) -> dict:
    return {"release_id": str(release_id), "seal_status": "UNKNOWN"}


@router.get("")
async def list_seals(
    seal_status: str | None = Query(None),
    verdict: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    return {"seals": [], "total": 0, "limit": limit, "offset": offset}