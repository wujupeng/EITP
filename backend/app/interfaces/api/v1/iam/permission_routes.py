"""IAM 权限管理路由。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/iam/permissions", tags=["iam-permission"])