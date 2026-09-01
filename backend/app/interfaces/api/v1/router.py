"""API v1 路由聚合 - 挂载各 Bounded Context 的路由模块。"""

from __future__ import annotations

from fastapi import APIRouter

from app.interfaces.api.v1.backup import router as backup_router
from app.interfaces.api.v1.config import router as config_router
from app.interfaces.api.v1.e2e_routes import router as e2e_router
from app.interfaces.api.v1.group import router as group_router
from app.interfaces.api.v1.hierarchy import router as hierarchy_router
from app.interfaces.api.v1.iam import iam_router
from app.interfaces.api.v1.inv import inv_router
from app.interfaces.api.v1.master_data import router as master_data_router
from app.interfaces.api.v1.mdm import mdm_router
from app.interfaces.api.v1.placement import router as placement_router
from app.interfaces.api.v1.pur import pur_router
from app.interfaces.api.v1.sal import sal_router
from app.interfaces.api.v1.tenant import router as tenant_router
from app.interfaces.api.v1.wms import wms_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(hierarchy_router)
api_router.include_router(tenant_router)
api_router.include_router(config_router)
api_router.include_router(group_router)
api_router.include_router(master_data_router)
api_router.include_router(placement_router)
api_router.include_router(backup_router)
api_router.include_router(iam_router)
api_router.include_router(inv_router)
api_router.include_router(mdm_router)
api_router.include_router(wms_router)
api_router.include_router(pur_router)
api_router.include_router(sal_router)
api_router.include_router(e2e_router)
