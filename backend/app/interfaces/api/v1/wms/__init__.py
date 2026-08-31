"""WMS 路由聚合。"""

from __future__ import annotations

from fastapi import APIRouter

from app.interfaces.api.v1.wms.space_routes import router as space_router
from app.interfaces.api.v1.wms.inventory_position_routes import router as inventory_position_router
from app.interfaces.api.v1.wms.task_routes import router as task_router
from app.interfaces.api.v1.wms.receiving_routes import router as receiving_router
from app.interfaces.api.v1.wms.putaway_routes import router as putaway_router
from app.interfaces.api.v1.wms.picking_routes import router as picking_router
from app.interfaces.api.v1.wms.transfer_routes import router as transfer_router
from app.interfaces.api.v1.wms.shipping_routes import router as shipping_router
from app.interfaces.api.v1.wms.reconcile_routes import router as reconcile_router

wms_router = APIRouter()
wms_router.include_router(space_router)
wms_router.include_router(inventory_position_router)
wms_router.include_router(task_router)
wms_router.include_router(receiving_router)
wms_router.include_router(putaway_router)
wms_router.include_router(picking_router)
wms_router.include_router(transfer_router)
wms_router.include_router(shipping_router)
wms_router.include_router(reconcile_router)