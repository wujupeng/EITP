"""FIN 路由聚合 - 七大子域路由聚合为 fin_routes。"""

from __future__ import annotations

from fastapi import APIRouter

from app.interfaces.api.v1.fin.routes.accounting_routes import router as accounting_router
from app.interfaces.api.v1.fin.routes.invoice_routes import router as invoice_router
from app.interfaces.api.v1.fin.routes.payment_routes import router as payment_router
from app.interfaces.api.v1.fin.routes.receipt_routes import (
    collection_router,
    router as receipt_router,
)
from app.interfaces.api.v1.fin.routes.reconciliation_routes import (
    router as reconciliation_router,
)
from app.interfaces.api.v1.fin.routes.settlement_routes import (
    router as settlement_router,
)
from app.interfaces.api.v1.fin.routes.treasury_routes import router as treasury_router

fin_routes = APIRouter(prefix="/fin", tags=["EITP-FIN-001"])
fin_routes.include_router(settlement_router)
fin_routes.include_router(payment_router)
fin_routes.include_router(receipt_router)
fin_routes.include_router(collection_router)
fin_routes.include_router(invoice_router)
fin_routes.include_router(reconciliation_router)
fin_routes.include_router(accounting_router)
fin_routes.include_router(treasury_router)