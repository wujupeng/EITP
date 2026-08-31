"""location_config_routes - inv-location 路由骨架。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/inv/locations", tags=["inv-location"])
