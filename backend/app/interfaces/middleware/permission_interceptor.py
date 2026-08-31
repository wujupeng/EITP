"""权限拦截器 - 基于 SecurityContext 的 API 权限校验。

fail-closed 原则：任何原因无法明确"允许"时统一拒绝。
"""

from __future__ import annotations

from functools import wraps
from typing import Callable

from fastapi import Request

from app.interfaces.middleware.error_handler import IAMError, IAMErrorCode
from app.interfaces.middleware.security_context import SecurityContext


def require_permission(permission_code: str) -> Callable:
    """权限校验装饰器。"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            ctx = SecurityContext.current()
            if ctx is None:
                raise IAMError(
                    IAMErrorCode.TOKEN_MISSING,
                    "未认证，缺少安全上下文",
                )

            if not ctx.is_authorized(permission_code):
                raise IAMError(
                    IAMErrorCode.PERMISSION_DENIED,
                    f"权限不足，需要: {permission_code}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_platform_admin() -> Callable:
    """平台管理员校验装饰器。"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            ctx = SecurityContext.current()
            if ctx is None:
                raise IAMError(IAMErrorCode.TOKEN_MISSING, "未认证")
            if not ctx.user.is_platform_admin:
                raise IAMError(
                    IAMErrorCode.PERMISSION_DENIED,
                    "需要平台管理员权限",
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_tenant_admin() -> Callable:
    """租户管理员校验装饰器。"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            ctx = SecurityContext.current()
            if ctx is None:
                raise IAMError(IAMErrorCode.TOKEN_MISSING, "未认证")
            if not (ctx.user.is_platform_admin or ctx.user.is_tenant_admin):
                raise IAMError(
                    IAMErrorCode.PERMISSION_DENIED,
                    "需要租户管理员权限",
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator