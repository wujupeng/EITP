"""FastAPI 应用入口 - EITP Multi-Tenant 应用面。

ASGI 入口：uvicorn app.main:app
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from app.config import get_settings
from app.infrastructure.db.session import close_engine
from app.interfaces.api.v1.health import router as health_router
from app.interfaces.api.v1.router import api_router
from app.interfaces.middleware.error_handler import setup_exception_handlers
from app.interfaces.middleware.tenant_context import TenantContextMiddleware
from app.interfaces.middleware.trace import TraceMiddleware
from app.logging_config import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期 - 启动与关闭钩子。"""
    settings = get_settings()
    setup_logging(level=settings.log_level, json_output=settings.log_json)
    yield
    await close_engine()


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

    app.add_middleware(TraceMiddleware)
    app.add_middleware(TenantContextMiddleware)

    setup_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router)

    return app


app = create_app()