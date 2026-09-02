"""PROD API 路由聚合。"""

from __future__ import annotations

from fastapi import APIRouter

from app.interfaces.api.v1.prod.core_freeze_routes import router as core_freeze_router
from app.interfaces.api.v1.prod.dossier_routes import router as dossier_router
from app.interfaces.api.v1.prod.evidence_routes import router as evidence_router
from app.interfaces.api.v1.prod.verification_routes import router as verification_router

prod_router = APIRouter(tags=["EITP-PROD-001"])
prod_router.include_router(verification_router)
prod_router.include_router(evidence_router)
prod_router.include_router(dossier_router)
prod_router.include_router(core_freeze_router)