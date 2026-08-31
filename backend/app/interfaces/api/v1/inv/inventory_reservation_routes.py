"""inventory_reservation_routes - inv-reservation 路由骨架。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/inv/inventory/reservations", tags=["inv-reservation"])
