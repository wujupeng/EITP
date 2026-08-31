"""IAM 路由聚合。"""

from __future__ import annotations

from fastapi import APIRouter

from app.interfaces.api.v1.iam.audit_routes import router as audit_router
from app.interfaces.api.v1.iam.auth_routes import router as auth_router
from app.interfaces.api.v1.iam.data_scope_routes import router as data_scope_router
from app.interfaces.api.v1.iam.department_routes import router as department_router
from app.interfaces.api.v1.iam.permission_routes import router as permission_router
from app.interfaces.api.v1.iam.platform_iam_routes import router as platform_iam_router
from app.interfaces.api.v1.iam.role_routes import router as role_router
from app.interfaces.api.v1.iam.user_routes import router as user_router

iam_router = APIRouter()
iam_router.include_router(auth_router)
iam_router.include_router(user_router)
iam_router.include_router(role_router)
iam_router.include_router(permission_router)
iam_router.include_router(data_scope_router)
iam_router.include_router(department_router)
iam_router.include_router(audit_router)
iam_router.include_router(platform_iam_router)