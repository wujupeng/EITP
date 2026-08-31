"""IAM 部门岗位路由。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/iam/departments", tags=["iam-org"])