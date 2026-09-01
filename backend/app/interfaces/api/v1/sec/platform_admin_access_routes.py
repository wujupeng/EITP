"""平台管理员访问申请路由。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from app.interfaces.middleware.permission_interceptor import require_permission

router = APIRouter(prefix="/sec/platform-admin-access", tags=["sec-platform-admin-access"])


class SubmitAccessRequest(BaseModel):
    target_tenant_id: str
    target_data_scope: str
    reason: str


class RejectRequest(BaseModel):
    reason: str


@router.post("/requests")
@require_permission("sec:platform:access:request")
async def submit_request(req: SubmitAccessRequest) -> dict:
    return {"request_id": "pending", "status": "pending"}


@router.get("/requests")
@require_permission("sec:platform:access:request")
async def list_requests(status: str | None = None) -> dict:
    return {"requests": [], "total": 0}


@router.post("/requests/{request_id}/approve")
@require_permission("sec:platform:access:approve")
async def approve_request(request_id: UUID) -> dict:
    return {"request_id": str(request_id), "status": "granted", "temp_permission_ttl": 7200}


@router.post("/requests/{request_id}/reject")
@require_permission("sec:platform:access:approve")
async def reject_request(request_id: UUID, req: RejectRequest) -> dict:
    return {"request_id": str(request_id), "status": "rejected", "reason": req.reason}