"""PUR 路由聚合。"""

from __future__ import annotations

from fastapi import APIRouter

from app.interfaces.api.v1.pur.asn_routes import router as asn_router
from app.interfaces.api.v1.pur.invoice_routes import router as invoice_router
from app.interfaces.api.v1.pur.order_routes import router as order_router
from app.interfaces.api.v1.pur.payment_routes import router as payment_router
from app.interfaces.api.v1.pur.quotation_routes import router as quotation_router
from app.interfaces.api.v1.pur.receipt_routes import router as receipt_router
from app.interfaces.api.v1.pur.reconcile_routes import router as reconcile_router
from app.interfaces.api.v1.pur.request_routes import router as request_router
from app.interfaces.api.v1.pur.return_routes import router as return_router
from app.interfaces.api.v1.pur.settlement_routes import router as settlement_router
from app.interfaces.api.v1.pur.supplier_routes import router as supplier_router

pur_router = APIRouter()
pur_router.include_router(supplier_router)
pur_router.include_router(quotation_router)
pur_router.include_router(request_router)
pur_router.include_router(order_router)
pur_router.include_router(asn_router)
pur_router.include_router(receipt_router)
pur_router.include_router(return_router)
pur_router.include_router(settlement_router)
pur_router.include_router(invoice_router)
pur_router.include_router(payment_router)
pur_router.include_router(reconcile_router)
