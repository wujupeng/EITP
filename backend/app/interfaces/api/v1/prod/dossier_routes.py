"""证明书管理 API 路由 - 5 个接口。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel
from structlog import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/prod/dossiers", tags=["PROD-Dossier"])


class DossierAssembleRequest(BaseModel):
    run_ids: list[str]
    tenant_scope: str
    tenant_id: str


class DossierSignRequest(BaseModel):
    signer_id: str
    tenant_id: str


@router.post("/assemble")
async def assemble_dossier(req: DossierAssembleRequest) -> dict:
    logger.info("dossier_assemble", runs=len(req.run_ids))
    return {
        "dossier_id": "pending",
        "status": "DRAFT",
        "evidence_count": len(req.run_ids),
    }


@router.get("/{dossier_id}")
async def get_dossier(dossier_id: UUID) -> dict:
    return {"dossier_id": str(dossier_id), "status": "NOT_FOUND"}


@router.get("")
async def list_dossiers(
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict:
    return {"items": [], "total": 0, "limit": limit, "offset": offset}


@router.post("/{dossier_id}/sign")
async def sign_dossier(dossier_id: UUID, req: DossierSignRequest) -> dict:
    logger.info("dossier_sign", dossier_id=str(dossier_id), signer=req.signer_id)
    return {
        "dossier_id": str(dossier_id),
        "status": "SIGNED",
        "signer": req.signer_id,
    }


@router.get("/{dossier_id}/export")
async def export_dossier(dossier_id: UUID) -> dict:
    logger.info("dossier_export", dossier_id=str(dossier_id))
    return {"dossier_id": str(dossier_id), "export_url": "pending"}