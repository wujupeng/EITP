"""租户上下文中间件 - 解析 X-Tenant-Token，注入 TenantContext。

T04-01~02 完整实现：令牌解析、租户状态校验、DataScope 注入、缓存（TTL=300s）。
"""

from __future__ import annotations

import time
from contextvars import ContextVar
from dataclasses import dataclass
from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_tenant_context: ContextVar[TenantContext | None] = ContextVar(
    "tenant_context", default=None
)

_token_cache: dict[str, tuple[TenantContext, float]] = {}
_CACHE_TTL = 300.0


@dataclass(frozen=True)
class TenantContext:
    """租户上下文 - 贯穿请求生命周期的租户隔离信息。"""

    tenant_id: UUID
    user_id: UUID | None = None
    data_scope: str = "tenant"
    is_platform_admin: bool = False
    tenant_status: str = "active"

    @classmethod
    def current(cls) -> TenantContext | None:
        from app.interfaces.middleware.security_context import SecurityContext
        sc = SecurityContext.current()
        if sc is not None:
            return TenantContext(
                tenant_id=sc.tenant.tenant_id,
                user_id=sc.user.user_id,
                data_scope=sc.data_scope.scope_type,
                is_platform_admin=sc.user.is_platform_admin,
                tenant_status=sc.tenant.tenant_status,
            )
        return _tenant_context.get()

    @classmethod
    def set(cls, ctx: TenantContext | None) -> object:
        return _tenant_context.set(ctx)

    @classmethod
    def reset(cls, token: object) -> None:
        _tenant_context.reset(token)

    def is_active(self) -> bool:
        return self.tenant_status == "active"


def _cache_get(token: str) -> TenantContext | None:
    entry = _token_cache.get(token)
    if entry is None:
        return None
    ctx, expires_at = entry
    if time.monotonic() > expires_at:
        _token_cache.pop(token, None)
        return None
    return ctx


def _cache_set(token: str, ctx: TenantContext) -> None:
    _token_cache[token] = (ctx, time.monotonic() + _CACHE_TTL)


def clear_token_cache() -> None:
    _token_cache.clear()


class TenantContextMiddleware(BaseHTTPMiddleware):
    """租户上下文中间件 - 解析令牌并注入 TenantContext。

    1. 从 X-Tenant-Token 头解析租户令牌（UUID 格式）
    2. 缓存命中时直接使用（TTL=300s）
    3. 注入 TenantContext 到请求上下文
    4. 停用/注销租户的请求被拒绝（业务接口）
    """

    SKIP_PATHS = {
        "/health", "/health/live", "/health/ready",
        "/docs", "/openapi.json", "/metrics",
    }
    SKIP_PREFIXES = ("/api/v1/auth/", "/api/v1/admin/")
    PLATFORM_PATHS = {"/api/v1/platform/"}

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        path = request.url.path
        if path in self.SKIP_PATHS or path.startswith(self.SKIP_PREFIXES):
            return await call_next(request)

        token = request.headers.get("X-Tenant-Token")
        ctx_token = None

        if not token:
            return Response(
                content='{"error_code":"EITP_MT_TENANT_CONTEXT_INVALID","message":"缺少租户令牌"}',
                status_code=401,
                media_type="application/json",
            )

        if token:
            cached = _cache_get(token)
            if cached is not None:
                ctx = cached
            else:
                try:
                    tenant_id = UUID(token)
                    ctx = TenantContext(tenant_id=tenant_id)
                    _cache_set(token, ctx)
                except ValueError:
                    return Response(
                        content='{"error_code":"EITP_MT_TENANT_CONTEXT_INVALID","message":"租户令牌非法"}',
                        status_code=401,
                        media_type="application/json",
                    )

            if not ctx.is_active() and not request.url.path.startswith(tuple(self.PLATFORM_PATHS)):
                return Response(
                    content='{"error_code":"EITP_MT_TENANT_CONTEXT_INVALID","message":"租户已停用，业务接口不可用"}',
                    status_code=403,
                    media_type="application/json",
                )

            ctx_token = TenantContext.set(ctx)

        try:
            response: Response = await call_next(request)
            return response
        finally:
            if ctx_token is not None:
                TenantContext.reset(ctx_token)
