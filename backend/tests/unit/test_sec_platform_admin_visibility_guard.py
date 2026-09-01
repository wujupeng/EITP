"""EITP-SEC-001 PlatformAdminVisibilityGuard 中间件单元测试。

覆盖业务数据访问拦截、运营元数据白名单放行、临时权限 TTL 放行。
使用轻量 mock request 与 call_next，避免完整 ASGI 协议栈。
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from starlette.responses import Response

from app.interfaces.middleware.platform_admin_visibility_guard import (
    PlatformAdminVisibilityGuard,
)
from app.interfaces.middleware.error_handler import SECError, SECErrorCode

_TEMP_PERMISSION_TTL = 7200


def _make_request(path: str, is_platform_admin: bool = False, has_temp: bool = False) -> Any:
    """构造轻量 mock request，仅暴露 dispatch 所需属性。"""
    return SimpleNamespace(
        url=SimpleNamespace(path=path),
        state=SimpleNamespace(
            is_platform_admin=is_platform_admin,
            has_platform_temp_permission=has_temp,
        ),
    )


async def _call_next_ok(request: Any) -> Response:
    return Response(content="ok", status_code=200)


def _make_guard() -> PlatformAdminVisibilityGuard:
    # BaseHTTPMiddleware 需要 app 参数；传入 dummy ASGI app
    return PlatformAdminVisibilityGuard(app=lambda *a, **kw: None)


class PlatformAdminVisibilityGuardTest:
    """PlatformAdminVisibilityGuard 可见性守卫。"""

    async def test_whitelist_route_tenants_passes(self) -> None:
        guard = _make_guard()
        request = _make_request("/api/v1/platform/tenants", is_platform_admin=True)
        response = await guard.dispatch(request, _call_next_ok)
        assert response.status_code == 200

    async def test_whitelist_route_tenant_usage_passes(self) -> None:
        guard = _make_guard()
        request = _make_request("/api/v1/platform/tenant-usage", is_platform_admin=True)
        response = await guard.dispatch(request, _call_next_ok)
        assert response.status_code == 200

    async def test_whitelist_route_health_passes(self) -> None:
        guard = _make_guard()
        request = _make_request("/api/v1/health", is_platform_admin=True)
        response = await guard.dispatch(request, _call_next_ok)
        assert response.status_code == 200

    async def test_non_business_route_passes_for_platform_admin(self) -> None:
        guard = _make_guard()
        request = _make_request("/api/v1/iam/users", is_platform_admin=True)
        response = await guard.dispatch(request, _call_next_ok)
        assert response.status_code == 200

    async def test_business_route_passes_for_non_platform_admin(self) -> None:
        guard = _make_guard()
        request = _make_request("/api/v1/inv/products", is_platform_admin=False)
        response = await guard.dispatch(request, _call_next_ok)
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "route",
        [
            "/api/v1/inv/products",
            "/api/v1/mdm/products",
            "/api/v1/wms/locations",
            "/api/v1/pur/orders",
            "/api/v1/sal/orders",
        ],
    )
    async def test_business_route_blocked_for_platform_admin(self, route: str) -> None:
        guard = _make_guard()
        request = _make_request(route, is_platform_admin=True)
        with pytest.raises(SECError) as exc:
            await guard.dispatch(request, _call_next_ok)
        assert exc.value.code == SECErrorCode.PLATFORM_ADMIN_BUSINESS_DATA_DENIED
        assert route in exc.value.message

    async def test_business_route_allowed_with_temp_permission(self) -> None:
        guard = _make_guard()
        request = _make_request(
            "/api/v1/inv/products", is_platform_admin=True, has_temp=True
        )
        response = await guard.dispatch(request, _call_next_ok)
        assert response.status_code == 200

    async def test_temp_permission_check_reads_state_flag(self) -> None:
        guard = _make_guard()
        request = _make_request("/api/v1/wms/locations", is_platform_admin=True)
        # 无临时权限 → 拒绝
        assert await guard._check_temp_permission(request) is False
        with pytest.raises(SECError):
            await guard.dispatch(request, _call_next_ok)
        # 有临时权限 → 放行
        request.state.has_platform_temp_permission = True
        assert await guard._check_temp_permission(request) is True
        response = await guard.dispatch(request, _call_next_ok)
        assert response.status_code == 200

    async def test_temp_permission_ttl_is_7200_seconds(self) -> None:
        # 守卫模块常量校验：临时权限 TTL = 2 小时
        import app.interfaces.middleware.platform_admin_visibility_guard as mod

        assert mod._TEMP_PERMISSION_TTL == _TEMP_PERMISSION_TTL == 7200

    async def test_business_route_subpath_blocked(self) -> None:
        guard = _make_guard()
        request = _make_request("/api/v1/inv/products/123/detail", is_platform_admin=True)
        with pytest.raises(SECError):
            await guard.dispatch(request, _call_next_ok)

    async def test_whitelist_route_takes_precedence_over_business_check(self) -> None:
        # /api/v1/platform/tenants 不在 _BUSINESS_ROUTES，白名单优先放行
        guard = _make_guard()
        request = _make_request("/api/v1/platform/tenants/abc/config", is_platform_admin=True)
        response = await guard.dispatch(request, _call_next_ok)
        assert response.status_code == 200

    async def test_log_access_does_not_raise(self) -> None:
        guard = _make_guard()
        request = _make_request("/api/v1/inv/products", is_platform_admin=True, has_temp=True)
        # _log_access 为空实现，应静默通过
        await guard._log_access(request)