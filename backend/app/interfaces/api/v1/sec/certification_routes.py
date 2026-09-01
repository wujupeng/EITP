"""认证执行与轮询路由。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission

router = APIRouter(prefix="/sec/certification", tags=["sec-certification"])


class ExecuteCertificationRequest(BaseModel):
    matrix_version: str = "v1.0"
    scope: str = Field(default="full", description="full/layers/modules/redis/visibility/join/e2e")
    layers: list[str] | None = None
    modules: list[str] | None = None
    trigger_source: str = "manual"


@router.post("/execute")
@require_permission("sec:cert:execute")
async def execute_certification(req: ExecuteCertificationRequest) -> dict:
    return {"batch_id": "pending", "status": "started", "scope": req.scope}


@router.get("/batches/{batch_id}")
@require_permission("sec:cert:execute")
async def get_batch_progress(batch_id: UUID) -> dict:
    return {"batch_id": str(batch_id), "status": "unknown", "total_items": 0, "passed": 0, "failed": 0, "unexecutable": 0}