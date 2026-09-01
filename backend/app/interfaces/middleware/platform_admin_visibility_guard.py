"""PlatformAdminVisibilityGuard - 平台管理员可见性守卫中间件。"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.interfaces.middleware.error_handler import SECError, SECErrorCode

_BUSINESS_ROUTES = ("/api/v1/inv/", "/api/v1/mdm/", "/api/v1/wms/", "/api/v1/pur/", "/api/v1/sal/")
_WHITELIST_ROUTES = ("/api/v1/platform/tenants", "/api/v1/platform/tenant-usage", "/api/v1/health")
_TEMP_PERMISSION_TTL = 7200


class PlatformAdminVisibilityGuard(BaseHTTPMiddleware):
    """拦截平台管理员直接访问业务数据明细。"""

    def __init__(self, app: Any, session_factory: Any = None) -> None:
        super().__init__(app)
        self._session_factory = session_factory

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        path = request.url.path
        if any(path.startswith(wl) for wl in _WHITELIST_ROUTES):
            return await call_next(request)

        if not any(path.startswith(br) for br in _BUSINESS_ROUTES):
            return await call_next(request)

        is_platform_admin = getattr(request.state, "is_platform_admin", False)
        if not is_platform_admin:
            return await call_next(request)

        has_temp_permission = await self._check_temp_permission(request)
        if has_temp_permission:
            await self._log_access(request)
            return await call_next(request)

        raise SECError(
            SECErrorCode.PLATFORM_ADMIN_BUSINESS_DATA_DENIED,
            f"Platform admin access denied for business route {path}",
        )

    async def _check_temp_permission(self, request: Request) -> bool:
        return getattr(request.state, "has_platform_temp_permission", False)

    async def _log_access(self, request: Request) -> None:
        pass