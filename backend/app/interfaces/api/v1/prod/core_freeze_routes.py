"""Core Freeze 监控 API 路由 - 2 个接口。"""

from __future__ import annotations

from fastapi import APIRouter
from structlog import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/prod/core-freeze", tags=["PROD-CoreFreeze"])


@router.get("/fingerprints")
async def get_core_freeze_fingerprints() -> dict:
    return {
        "milestones": ["MT", "IAM", "INV", "MDM", "WMS", "PUR", "SAL", "SEC", "PLT"],
        "asset_types": ["model", "api_contract", "table_ddl", "rls_policy"],
        "fingerprints": [],
    }


@router.post("/verify")
async def verify_core_freeze() -> dict:
    logger.info("core_freeze_verify")
    return {
        "violations": [],
        "violation_count": 0,
        "all_ok": True,
    }