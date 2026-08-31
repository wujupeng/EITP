"""FastAPI 应用入口 - EITP Multi-Tenant 应用面。

ASGI 入口：uvicorn app.main:app
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.infrastructure.cache.redis_client import close_redis
from app.infrastructure.db.session import close_engine, get_session_factory
from app.infrastructure.observability.metrics import setup_metrics_endpoint
from app.application.scheduler.inv_scheduler import InvScheduler
from app.application.scheduler.mdm_scheduler import MdmScheduler
from app.application.scheduler.wms_scheduler import WmsScheduler
from app.domain.warehouse.services.red_line_guard import validate_red_line_on_startup
from app.interfaces.api.v1.health import router as health_router
from app.interfaces.api.v1.router import api_router
from app.interfaces.middleware.error_handler import setup_exception_handlers
from app.interfaces.middleware.tenant_context import TenantContextMiddleware
from app.interfaces.middleware.security_context_middleware import SecurityContextMiddleware
from app.interfaces.middleware.feature_flag_guard import FeatureFlagGuard
from app.interfaces.middleware.trace import TraceMiddleware
from app.logging_config import setup_logging

logger = logging.getLogger(__name__)

_scheduler: InvScheduler | None = None
_mdm_scheduler: MdmScheduler | None = None
_wms_scheduler: WmsScheduler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期 - 启动与关闭钩子。"""
    global _scheduler, _mdm_scheduler, _wms_scheduler
    settings = get_settings()
    setup_logging(level=settings.log_level, json_output=settings.log_json)
    _scheduler = InvScheduler()
    await _scheduler.start()
    logger.info("INV scheduler started with 5 periodic tasks")
    _mdm_scheduler = MdmScheduler()
    await _mdm_scheduler.start()
    logger.info("MDM scheduler started with 6 periodic tasks")
    _wms_scheduler = WmsScheduler()
    await _wms_scheduler.start()
    logger.info("WMS scheduler started with 3 periodic tasks")
    try:
        passed = await validate_red_line_on_startup(get_session_factory)
        if not passed:
            logger.warning(
                "WMS red line validation failed - WMS service account has direct write "
                "privileges on inv_* tables. This violates the first red line. "
                "RLS enforcement will be applied in T10 migration."
            )
    except Exception as exc:
        logger.warning("WMS red line validation skipped: %s", str(exc))
    yield
    if _mdm_scheduler is not None:
        await _mdm_scheduler.stop()
        logger.info("MDM scheduler stopped")
    if _wms_scheduler is not None:
        await _wms_scheduler.stop()
        logger.info("WMS scheduler stopped")
    if _scheduler is not None:
        await _scheduler.stop()
        logger.info("INV scheduler stopped")
    await close_engine()
    await close_redis()


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例。"""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="EITP Multi-Tenant 多企业统一进销存交易平台 - 应用面",
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    # Starlette 中间件栈 LIFO：后添加先执行。
    # 期望请求执行顺序：CORS → Trace → TenantContext → SecurityContext → FeatureFlagGuard → Route
    app.add_middleware(FeatureFlagGuard)
    app.add_middleware(SecurityContextMiddleware)
    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(TraceMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    setup_exception_handlers(app)
    setup_metrics_endpoint(app)

    app.include_router(health_router)
    app.include_router(api_router)

    return app


app = create_app()