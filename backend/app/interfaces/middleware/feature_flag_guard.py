"""FeatureFlagGuard - 功能开关校验中间件。

C-CONFIG-02: 关闭功能对应接口立即拒绝。
C-CONFIG-01: 开关切换即时失效缓存（TTL=60s）。
"""

from __future__ import annotations

import time
from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_feature_cache: dict[str, tuple[bool, float]] = {}
_CACHE_TTL = 60.0

FEATURE_PATH_MAP: dict[str, str] = {
    "/api/v1/tenant/hierarchy": "hierarchy",
    "/api/v1/tenant/config": "config",
    "/api/v1/inv/": "inventory",
    "/api/v1/group/": "mdm_group_catalog",
    "/api/v1/tenant/mdm/enterprise-products": "mdm_enterprise_product",
    "/api/v1/tenant/mdm/governance": "mdm_governance",
    "/api/v1/tenant/mdm/negative-policy": "mdm_negative_policy",
}


def _cache_get(key: str) -> bool | None:
    entry = _feature_cache.get(key)
    if entry is None:
        return None
    value, expires_at = entry
    if time.monotonic() > expires_at:
        _feature_cache.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: bool) -> None:
    _feature_cache[key] = (value, time.monotonic() + _CACHE_TTL)


def clear_feature_cache() -> None:
    _feature_cache.clear()


class FeatureFlagGuard(BaseHTTPMiddleware):
    """功能开关守卫 - 校验请求路径对应的功能是否开启。

    关闭功能时对应接口立即拒绝（返回 403）。
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        path = request.url.path

        for prefix, feature_key in FEATURE_PATH_MAP.items():
            if path.startswith(prefix):
                cache_key = f"{feature_key}:{request.headers.get('X-Tenant-Token', '')}"
                cached = _cache_get(cache_key)

                if cached is False:
                    return Response(
                        content='{"error_code":"EITP_MT_FEATURE_DISABLED","message":"功能已关闭"}',
                        status_code=403,
                        media_type="application/json",
                    )

        return await call_next(request)