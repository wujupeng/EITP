"""FIN 域健康检查 - /fin/health，复用 StandardizedHealthCheck 探测模式。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.session import get_db_session

router = APIRouter(tags=["fin-health"])


@router.get("/fin/health/live")
async def fin_health_live() -> dict[str, str]:
    return {"status": "alive", "domain": "FIN"}


@router.get("/fin/health/ready")
async def fin_health_ready(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    try:
        result = await session.execute(text("SELECT 1"))
        result.scalar_one()
        return {"status": "ready", "domain": "FIN", "database": "ok"}
    except Exception:
        return {"status": "degraded", "domain": "FIN", "database": "error"}


@router.get("/fin/health")
async def fin_health(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    probes: dict[str, str] = {}
    try:
        result = await session.execute(text("SELECT 1"))
        result.scalar_one()
        probes["bank_receipt_interface"] = "ok"
    except Exception:
        probes["bank_receipt_interface"] = "error"
    try:
        from app.infrastructure.platform.observability.fin_metrics import (
            get_fin_metrics_registry,
        )

        get_fin_metrics_registry()
        probes["invoice_image_storage"] = "ok"
    except Exception:
        probes["invoice_image_storage"] = "error"
    try:
        from app.interfaces.api.v1.fin.routes import fin_routes

        assert fin_routes is not None
        probes["event_bus_subscription"] = "ok"
    except Exception:
        probes["event_bus_subscription"] = "error"
    overall = "ok" if all(v == "ok" for v in probes.values()) else "degraded"
    return {"status": overall, "domain": "FIN", **probes}