"""证书管理路由。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from app.interfaces.middleware.permission_interceptor import require_permission

router = APIRouter(prefix="/sec/certificate", tags=["sec-certificate"])


class IssueCertificateRequest(BaseModel):
    batch_id: str
    issuer: str
    signer: str


class RevokeCertificateRequest(BaseModel):
    reason: str


@router.post("/issue")
@require_permission("sec:cert:issue")
async def issue_certificate(req: IssueCertificateRequest) -> dict:
    return {"cert_number": "pending", "status": "draft"}


@router.get("/current")
@require_permission("sec:cert:verify")
async def get_current_certificate() -> dict:
    return {"cert_number": None, "status": "none"}


@router.get("/{cert_id}")
@require_permission("sec:cert:verify")
async def get_certificate(cert_id: UUID) -> dict:
    return {"certificate_id": str(cert_id), "status": "unknown"}


@router.post("/{cert_id}/revoke")
@require_permission("sec:cert:revoke")
async def revoke_certificate(cert_id: UUID, req: RevokeCertificateRequest) -> dict:
    return {"certificate_id": str(cert_id), "status": "revoked", "reason": req.reason}


@router.get("/{cert_id}/verify")
@require_permission("sec:cert:verify")
async def verify_certificate(cert_id: UUID) -> dict:
    return {"certificate_id": str(cert_id), "signature_valid": True, "status_valid": True, "not_expired": True, "not_revoked": True, "overall_valid": True}