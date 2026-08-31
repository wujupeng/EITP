"""IAM 数据权限路由。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/iam/data-scopes", tags=["iam-data-scope"])