"""SAL 路由聚合。"""

from __future__ import annotations

from fastapi import APIRouter

from app.interfaces.api.v1.sal.category_routes import router as category_router
from app.interfaces.api.v1.sal.credit_routes import router as credit_router
from app.interfaces.api.v1.sal.customer_routes import router as customer_router
from app.interfaces.api.v1.sal.invoice_routes import router as invoice_router
from app.interfaces.api.v1.sal.order_routes import router as order_router
from app.interfaces.api.v1.sal.packing_routes import router as packing_router
from app.interfaces.api.v1.sal.payment_routes import router as payment_router
from app.interfaces.api.v1.sal.pricing_routes import router as pricing_router
from app.interfaces.api.v1.sal.quotation_routes import router as quotation_router
from app.interfaces.api.v1.sal.reconcile_routes import router as reconcile_router
from app.interfaces.api.v1.sal.return_routes import router as return_router
from app.interfaces.api.v1.sal.settlement_routes import router as settlement_router
from app.interfaces.api.v1.sal.shipment_routes import router as shipment_router

sal_router = APIRouter()
sal_router.include_router(customer_router)
sal_router.include_router(category_router)
sal_router.include_router(quotation_router)
sal_router.include_router(order_router)
sal_router.include_router(shipment_router)
sal_router.include_router(packing_router)
sal_router.include_router(return_router)
sal_router.include_router(settlement_router)
sal_router.include_router(invoice_router)
sal_router.include_router(payment_router)
sal_router.include_router(reconcile_router)
sal_router.include_router(credit_router)
sal_router.include_router(pricing_router)
