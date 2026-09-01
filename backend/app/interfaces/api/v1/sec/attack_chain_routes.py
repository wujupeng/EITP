"""攻击链 E2E 路由。"""

from __future__ import annotations

from fastapi import APIRouter

from app.interfaces.middleware.permission_interceptor import require_permission

router = APIRouter(prefix="/sec/attack-chain", tags=["sec-attack-chain"])


@router.post("/execute")
@require_permission("sec:attack:chain")
async def execute_attack_chain() -> dict:
    return {"chain_id": "pending", "total_steps": 14, "passed_steps": 0, "failed_steps": 0, "results": []}