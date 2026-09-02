"""PLT 平台基础设施 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter

from app.interfaces.api.v1.plt.audit_routes import router as audit_router
from app.interfaces.api.v1.plt.consistency_routes import router as consistency_router
from app.interfaces.api.v1.plt.idempotency_routes import router as idempotency_router
from app.interfaces.api.v1.plt.permission_routes import router as permission_router
from app.interfaces.api.v1.plt.tenant_routes import router as tenant_router
from app.interfaces.api.v1.plt.observability_routes import router as observability_router
from app.interfaces.api.v1.plt.config_routes import router as config_router
from app.interfaces.api.v1.plt.job_routes import router as job_router
from app.interfaces.api.v1.plt.api_governance_routes import router as api_governance_router
from app.interfaces.api.v1.plt.performance_routes import router as performance_router
from app.interfaces.api.v1.plt.cicd_routes import router as cicd_router

plt_router = APIRouter()
plt_router.include_router(audit_router)
plt_router.include_router(consistency_router)
plt_router.include_router(idempotency_router)
plt_router.include_router(permission_router)
plt_router.include_router(tenant_router)
plt_router.include_router(observability_router)
plt_router.include_router(config_router)
plt_router.include_router(job_router)
plt_router.include_router(api_governance_router)
plt_router.include_router(performance_router)
plt_router.include_router(cicd_router)
