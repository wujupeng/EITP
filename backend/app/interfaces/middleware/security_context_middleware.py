"""SecurityContext 组装中间件 - 从 JWT 组装 SecurityContext。

中间件链：Trace → TenantContext(MT-001) → SecurityContextAssembler(IAM) → PermissionInterceptor
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.infrastructure.auth.token_service import TokenService
from app.infrastructure.auth.token_revocation_service import get_revocation_service
from app.interfaces.middleware.error_handler import IAMErrorCode
from app.interfaces.middleware.security_context import (
    SecurityContext,
    UserIdentity,
    TenantIdentity,
    RoleSummary,
    PermissionSummary,
    ResolvedDataScope,
    AccessMode,
)

SKIP_PATHS = {
    "/health", "/health/live", "/health/ready",
    "/docs", "/openapi.json",
    "/api/v1/auth/login",
}


class SecurityContextMiddleware(BaseHTTPMiddleware):
    """从 Authorization Bearer JWT 组装 SecurityContext。"""

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return await call_next(request)

        token = auth_header[7:]
        token_svc = TokenService()

        try:
            claims = token_svc.verify_access_token(token)
        except Exception:
            return Response(
                content='{"error_code":"EITP_IAM_TOKEN_SIGNATURE_INVALID","message":"Token无效"}',
                status_code=401,
                media_type="application/json",
            )

        revocation_svc = get_revocation_service()
        if await revocation_svc.is_revoked(claims.jti):
            return Response(
                content='{"error_code":"EITP_IAM_TOKEN_REVOKED","message":"Token已撤销"}',
                status_code=401,
                media_type="application/json",
            )

        if await revocation_svc.is_user_revoked(str(claims.sub)):
            return Response(
                content='{"error_code":"EITP_IAM_TOKEN_REVOKED","message":"用户Token已全部撤销"}',
                status_code=401,
                media_type="application/json",
            )

        ctx = SecurityContext(
            user=UserIdentity(
                user_id=claims.sub,
                username="",
                is_platform_admin=claims.is_platform_admin,
                is_tenant_admin=claims.is_tenant_admin,
            ),
            tenant=TenantIdentity(tenant_id=claims.tenant_id),
            roles=tuple(
                RoleSummary(role_id=claims.sub, role_code=r, role_name=r)
                for r in claims.roles
            ),
            permissions=PermissionSummary(codes=frozenset(claims.permissions)),
            data_scope=ResolvedDataScope(
                scope_type="tenant" if not claims.is_platform_admin else "platform",
                access_mode=AccessMode.ADMIN if claims.is_platform_admin else AccessMode.READ,
            ),
        )

        ctx_token = SecurityContext.set(ctx)
        try:
            response: Response = await call_next(request)
            return response
        finally:
            SecurityContext.reset(ctx_token)