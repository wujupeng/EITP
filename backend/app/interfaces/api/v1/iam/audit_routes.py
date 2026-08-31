"""IAM 审计查询路由。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/iam/audit", tags=["iam-audit"])