"""count_routes - inv-count 路由骨架。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/inv/counts", tags=["inv-count"])
