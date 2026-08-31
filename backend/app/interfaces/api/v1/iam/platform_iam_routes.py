"""平台 IAM 管理路由 - 多租户管理员/企业管理员。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/platform/iam", tags=["platform-iam"])