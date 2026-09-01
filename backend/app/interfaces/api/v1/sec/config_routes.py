"""配置管理路由。"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.interfaces.middleware.permission_interceptor import require_permission

router = APIRouter(prefix="/sec/config", tags=["sec-config"])


class UpdateConfigRequest(BaseModel):
    strict_mode: bool | None = None
    alert_channels: list[str] | None = None
    report_retention_days: int | None = None


class SkipItemRequest(BaseModel):
    reason: str


@router.get("")
@require_permission("sec:config:manage")
async def get_config() -> dict:
    return {"strict_mode": True, "alert_channels": [], "report_retention_days": 365}


@router.put("")
@require_permission("sec:config:manage")
async def update_config(req: UpdateConfigRequest) -> dict:
    return {"updated": True}


@router.put("/items/{item_id}/skip")
@require_permission("sec:config:item:skip")
async def skip_item(item_id: str, req: SkipItemRequest) -> dict:
    if not req.reason:
        return {"error": "EITP_SEC_SKIP_REASON_REQUIRED"}
    return {"item_id": item_id, "skipped": True, "reason": req.reason}