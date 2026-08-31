"""adjustment_routes - inv-adjustment 路由骨架。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/inv/adjustments", tags=["inv-adjustment"])
