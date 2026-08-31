"""cost_routes - inv-cost 路由骨架。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/inv/costs", tags=["inv-cost"])
