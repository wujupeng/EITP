"""健康检查接口 - /health。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.session import get_db_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """存活检查 - 无依赖，仅返回应用状态。"""
    return {"status": "ok"}


@router.get("/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/health/ready")
async def health_ready(session: AsyncSession = Depends(get_db_session)) -> dict[str, str]:
    """就绪检查 - 验证数据库连接可用。"""
    try:
        result = await session.execute(text("SELECT 1"))
        result.scalar_one()
        return {"status": "ready", "database": "ok"}
    except Exception:
        return {"status": "degraded", "database": "error"}
