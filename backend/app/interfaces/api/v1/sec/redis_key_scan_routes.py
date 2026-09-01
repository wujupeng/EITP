"""Redis Key 扫描路由。"""

from __future__ import annotations

from fastapi import APIRouter

from app.interfaces.middleware.permission_interceptor import require_permission

router = APIRouter(prefix="/sec/redis-key-scan", tags=["sec-redis-scan"])


@router.post("")
@require_permission("sec:redis:scan")
async def scan_redis_keys() -> dict:
    return {"total_keys": 0, "violations": [], "compliance_rate": 1.0}