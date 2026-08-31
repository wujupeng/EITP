"""IAM 角色管理路由。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/iam/roles", tags=["iam-role"])