"""配置中心 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from structlog import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/plt/config", tags=["PLT-Config"])


class ConfigCreateRequest(BaseModel):
    namespace: str = Field(..., pattern="^(GLOBAL|TENANT|MODULE)$")
    namespace_id: str | None = None
    config_key: str
    config_value: dict
    value_type: str = Field(..., pattern="^(STRING|INT|FLOAT|BOOL|JSON|SECRET)$")
    description: str
    changed_by: str


@router.get("/revisions")
async def list_config_revisions(
    namespace: str | None = Query(None),
    config_key: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
) -> dict:
    return {"items": [], "total": 0}


@router.post("/revisions")
async def create_config_revision(req: ConfigCreateRequest) -> dict:
    logger.info("config_created", key=req.config_key, namespace=req.namespace)
    return {"revision_id": "created", "version": 1}


@router.get("/revisions/{revision_id}")
async def get_config_revision(revision_id: str) -> dict:
    return {"revision_id": revision_id, "found": False}


@router.get("/value/{config_key}")
async def get_config_value(
    config_key: str,
    namespace: str = Query("GLOBAL"),
    namespace_id: str | None = Query(None),
) -> dict:
    return {"config_key": config_key, "value": None}