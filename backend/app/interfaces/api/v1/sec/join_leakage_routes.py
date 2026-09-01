"""JOIN 泄露测试路由。"""

from __future__ import annotations

from fastapi import APIRouter

from app.interfaces.middleware.permission_interceptor import require_permission

router = APIRouter(prefix="/sec/join-leakage", tags=["sec-join-leakage"])


@router.post("/test")
@require_permission("sec:join:test")
async def test_join_leakage() -> dict:
    return {"test_id": "pending", "results": []}