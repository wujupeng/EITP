"""BIZ-OPS 路由聚合 - 挂载各子路由模块。"""

from __future__ import annotations

from fastapi import APIRouter

from app.interfaces.api.v1.biz_ops.routes.strategy_routes import router as strategy_router
from app.interfaces.api.v1.biz_ops.routes.strategy_routes import rule_router as business_rule_router
from app.interfaces.api.v1.biz_ops.routes.strategy_routes import pricing_router
from app.interfaces.api.v1.biz_ops.routes.strategy_routes import tax_router
from app.interfaces.api.v1.biz_ops.routes.strategy_routes import inv_strategy_router
from app.interfaces.api.v1.biz_ops.routes.operation_routes import router as operation_router
from app.interfaces.api.v1.biz_ops.routes.audit_routes import router as audit_router

biz_ops_router = APIRouter()
biz_ops_router.include_router(strategy_router)
biz_ops_router.include_router(business_rule_router)
biz_ops_router.include_router(pricing_router)
biz_ops_router.include_router(tax_router)
biz_ops_router.include_router(inv_strategy_router)
biz_ops_router.include_router(operation_router)
biz_ops_router.include_router(audit_router)
