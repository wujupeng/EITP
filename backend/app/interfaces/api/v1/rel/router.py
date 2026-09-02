"""REL API 路由聚合。"""

from __future__ import annotations

from fastapi import APIRouter

from app.interfaces.api.v1.rel.declaration_routes import router as declaration_router
from app.interfaces.api.v1.rel.gate_routes import router as gate_router
from app.interfaces.api.v1.rel.report_routes import router as report_router
from app.interfaces.api.v1.rel.rollback_routes import router as rollback_router
from app.interfaces.api.v1.rel.seal_routes import router as seal_router
from app.interfaces.api.v1.rel.snapshot_routes import router as snapshot_router

rel_router = APIRouter(tags=["EITP-REL-001"])
rel_router.include_router(seal_router)
rel_router.include_router(gate_router)
rel_router.include_router(snapshot_router)
rel_router.include_router(declaration_router)
rel_router.include_router(report_router)
rel_router.include_router(rollback_router)