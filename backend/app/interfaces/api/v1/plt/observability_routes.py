"""Observability API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Response
from structlog import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/plt/observability", tags=["PLT-Observability"])


@router.get("/metrics")
async def get_metrics() -> Response:
    from app.infrastructure.platform.observability.plt_metrics import get_metrics_registry

    registry = get_metrics_registry()
    return Response(content=registry.expose(), media_type="text/plain; version=0.0.4; charset=utf-8")


@router.get("/health")
async def health_check() -> dict:
    return {"status": "healthy", "checks": {}}


@router.get("/dashboard")
async def dashboard_overview() -> dict:
    return {
        "qps": 0,
        "p95": 0,
        "p99": 0,
        "error_rate": 0,
        "active_tenants": 0,
        "outbox_pending": 0,
        "saga_running": 0,
    }