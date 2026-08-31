"""block_routes - inv-block 路由骨架。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/inv/blocks", tags=["inv-block"])
