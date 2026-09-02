"""性能基线 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from structlog import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/plt/performance", tags=["PLT-Performance"])


class BaselineCreateRequest(BaseModel):
    api_path: str
    p95_ms: float
    p99_ms: float
    qps: float


@router.get("/baselines")
async def list_baselines() -> dict:
    return {"items": [], "total": 0}


@router.post("/baselines")
async def create_baseline(req: BaselineCreateRequest) -> dict:
    logger.info("baseline_created", path=req.api_path, p95=req.p95_ms)
    return {"baseline_id": "created"}


@router.get("/regression-check")
async def regression_check() -> dict:
    return {"has_regression": False, "regressions": []}