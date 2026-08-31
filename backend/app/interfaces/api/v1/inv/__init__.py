"""INV 路由聚合。"""

from __future__ import annotations

from fastapi import APIRouter

from app.interfaces.api.v1.inv.product_routes import router as product_router
from app.interfaces.api.v1.inv.location_config_routes import router as location_config_router
from app.interfaces.api.v1.inv.inventory_query_routes import router as inventory_query_router
from app.interfaces.api.v1.inv.inventory_transaction_routes import router as inventory_transaction_router
from app.interfaces.api.v1.inv.inventory_reservation_routes import router as inventory_reservation_router
from app.interfaces.api.v1.inv.document_routes import router as document_router
from app.interfaces.api.v1.inv.count_routes import router as count_router
from app.interfaces.api.v1.inv.adjustment_routes import router as adjustment_router
from app.interfaces.api.v1.inv.block_routes import router as block_router
from app.interfaces.api.v1.inv.cost_routes import router as cost_router
from app.interfaces.api.v1.inv.inventory_audit_routes import router as inventory_audit_router
from app.interfaces.api.v1.inv.negative_stock_routes import router as negative_stock_router

inv_router = APIRouter()
inv_router.include_router(product_router)
inv_router.include_router(location_config_router)
inv_router.include_router(inventory_query_router)
inv_router.include_router(inventory_transaction_router)
inv_router.include_router(inventory_reservation_router)
inv_router.include_router(document_router)
inv_router.include_router(count_router)
inv_router.include_router(adjustment_router)
inv_router.include_router(block_router)
inv_router.include_router(cost_router)
inv_router.include_router(inventory_audit_router)
inv_router.include_router(negative_stock_router)
