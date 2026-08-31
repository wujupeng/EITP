"""inventory_audit_routes - inv-audit 路由骨架。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/inv/audits", tags=["inv-audit"])
