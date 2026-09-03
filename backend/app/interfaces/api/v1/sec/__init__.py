"""SEC 路由聚合 - 挂载多租户隔离认证各子模块路由。"""

from __future__ import annotations

from fastapi import APIRouter

from app.interfaces.api.v1.sec.certification_routes import router as certification_router
from app.interfaces.api.v1.sec.report_routes import router as report_router
from app.interfaces.api.v1.sec.certificate_routes import router as certificate_router
from app.interfaces.api.v1.sec.config_routes import router as config_router
from app.interfaces.api.v1.sec.audit_routes import router as audit_router
from app.interfaces.api.v1.sec.platform_admin_access_routes import router as platform_admin_access_router
from app.interfaces.api.v1.sec.redis_key_scan_routes import router as redis_key_scan_router
from app.interfaces.api.v1.sec.join_leakage_routes import router as join_leakage_router
from app.interfaces.api.v1.sec.attack_chain_routes import router as attack_chain_router

sec_router = APIRouter()
sec_router.include_router(certification_router)
sec_router.include_router(report_router)
sec_router.include_router(certificate_router)
sec_router.include_router(config_router)
sec_router.include_router(audit_router)
sec_router.include_router(platform_admin_access_router)
sec_router.include_router(redis_key_scan_router)
sec_router.include_router(join_leakage_router)
sec_router.include_router(attack_chain_router)
