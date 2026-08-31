"""negative_stock_routes - inv-negative-stock 路由骨架。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/inv/negative-stock", tags=["inv-negative-stock"])
