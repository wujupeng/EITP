"""Job Center API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from structlog import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/plt/job", tags=["PLT-Job"])


class JobCreateRequest(BaseModel):
    job_name: str
    cron_expression: str
    handler_ref: str
    timeout_seconds: int = 300
    concurrency_strategy: str = "FORBID"
    tenant_scope: str = "PLATFORM"


@router.get("/definitions")
async def list_job_definitions(enabled: bool | None = Query(None)) -> dict:
    return {"items": [], "total": 0}


@router.post("/definitions")
async def create_job_definition(req: JobCreateRequest) -> dict:
    logger.info("job_created", name=req.job_name)
    return {"job_id": "created", "job_name": req.job_name, "enabled": False}


@router.post("/definitions/{job_id}/enable")
async def enable_job(job_id: str) -> dict:
    return {"job_id": job_id, "enabled": True}


@router.post("/definitions/{job_id}/disable")
async def disable_job(job_id: str) -> dict:
    return {"job_id": job_id, "enabled": False}


@router.post("/definitions/{job_id}/execute")
async def execute_job(job_id: str) -> dict:
    logger.info("job_execute", job_id=job_id)
    return {"execution_id": "started", "job_id": job_id, "status": "RUNNING"}


@router.get("/executions")
async def list_job_executions(
    job_id: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
) -> dict:
    return {"items": [], "total": 0}