"""T04 租户隔离与安全边界单元测试 - 四层纵深隔离。"""

from __future__ import annotations

import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.db.rls_policy import PlacementMode, RLSPolicyManager, RLSPolicyProvider
from app.interfaces.middleware.data_scope_guard import (
    DataScope,
    DataScopeGuard,
    DataScopeLevel,
)
from app.interfaces.middleware.error_handler import DomainError, ErrorCode
from app.interfaces.middleware.tenant_context import (
    TenantContext,
    TenantContextMiddleware,
    clear_token_cache,
    _cache_get,
    _cache_set,
)
from app.main import create_app


class TestTenantContextMiddleware:
    def test_no_token_passes_health(self) -> None:
        app = create_app()
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_invalid_token_returns_401(self) -> None:
        app = create_app()
        client = TestClient(app)
        response = client.get("/api/v1/tenant/hierarchy/tree", headers={"X-Tenant-Token": "invalid"})
        assert response.status_code == 401
        assert "EITP_MT_TENANT_CONTEXT_INVALID" in response.text

    def test_valid_uuid_token_accepted(self) -> None:
        """有效 UUID 令牌通过中间件校验（不返回 401）。"""
        from app.interfaces.middleware.tenant_context import clear_token_cache
        clear_token_cache()
        token = str(uuid4())

        ctx = TenantContext(tenant_id=uuid4())
        from app.interfaces.middleware import tenant_context as tc_mod
        tc_mod._cache_set(token, ctx)

        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/v1/tenant/hierarchy/tree", headers={"X-Tenant-Token": token})
        assert response.status_code != 401

    def test_token_cache_hit(self) -> None:
        clear_token_cache()
        token = str(uuid4())
        tenant_id = uuid4()
        ctx = TenantContext(tenant_id=tenant_id)
        _cache_set(token, ctx)

        cached = _cache_get(token)
        assert cached is not None
        assert cached.tenant_id == tenant_id

    def test_token_cache_expiry(self) -> None:
        clear_token_cache()
        token = str(uuid4())
        ctx = TenantContext(tenant_id=uuid4())
        _cache_set(token, ctx)

        from app.interfaces.middleware import tenant_context as tc_mod
        original_cache = tc_mod._token_cache.copy()
        for k in tc_mod._token_cache:
            old_ctx, _ = original_cache[k]
            tc_mod._token_cache[k] = (old_ctx, time.monotonic() - 1)

        cached = _cache_get(token)
        assert cached is None

    def test_disabled_tenant_rejected(self) -> None:
        app = create_app()
        client = TestClient(app)
        token = str(uuid4())
        from app.interfaces.middleware import tenant_context as tc_mod
        tc_mod.clear_token_cache()
        ctx = TenantContext(tenant_id=uuid4(), tenant_status="disabled")
        tc_mod._cache_set(token, ctx)

        response = client.get("/api/v1/tenant/hierarchy/tree", headers={"X-Tenant-Token": token})
        assert response.status_code == 403
        assert "租户已停用" in response.text


class TestDataScopeGuard:
    def test_enforce_tenant_isolation_same_tenant(self) -> None:
        tenant_id = uuid4()
        ctx = TenantContext(tenant_id=tenant_id)
        DataScopeGuard.enforce_tenant_isolation(ctx, tenant_id)

    def test_enforce_tenant_isolation_cross_tenant_denied(self) -> None:
        ctx = TenantContext(tenant_id=uuid4())
        with pytest.raises(DomainError) as exc:
            DataScopeGuard.enforce_tenant_isolation(ctx, uuid4())
        assert exc.value.code == ErrorCode.CROSS_TENANT_REF_DENIED

    def test_platform_admin_cross_tenant_allowed(self) -> None:
        ctx = TenantContext(tenant_id=uuid4(), is_platform_admin=True)
        DataScopeGuard.enforce_tenant_isolation(ctx, uuid4())

    def test_resolve_scope_platform_admin(self) -> None:
        ctx = TenantContext(tenant_id=uuid4(), is_platform_admin=True)
        scope = DataScopeGuard.resolve_scope(ctx)
        assert scope.level == DataScopeLevel.PLATFORM

    def test_resolve_scope_tenant_user(self) -> None:
        ctx = TenantContext(tenant_id=uuid4())
        scope = DataScopeGuard.resolve_scope(ctx)
        assert scope.level == DataScopeLevel.ENTERPRISE

    def test_enforce_scope_subset_within_authorized(self) -> None:
        ids = (uuid4(), uuid4())
        scope = DataScope(tenant_id=uuid4(), level=DataScopeLevel.ENTERPRISE, scope_ids=ids)
        result = DataScopeGuard.enforce_scope_subset(scope, ids)
        assert result == ids

    def test_enforce_scope_subset_partial_violation(self) -> None:
        valid_id = uuid4()
        invalid_id = uuid4()
        scope = DataScope(tenant_id=uuid4(), level=DataScopeLevel.ENTERPRISE, scope_ids=(valid_id,))
        result = DataScopeGuard.enforce_scope_subset(scope, (valid_id, invalid_id))
        assert valid_id in result
        assert invalid_id not in result


class TestRLSPolicyManager:
    def test_shared_db_rls_active(self) -> None:
        mgr = RLSPolicyProvider.create(PlacementMode.SHARED_DB)
        assert mgr.is_rls_active() is True

    def test_dedicated_db_rls_inactive(self) -> None:
        mgr = RLSPolicyProvider.create(PlacementMode.DEDICATED_DB)
        assert mgr.is_rls_active() is False

    def test_dedicated_instance_rls_inactive(self) -> None:
        mgr = RLSPolicyProvider.create(PlacementMode.DEDICATED_INSTANCE)
        assert mgr.is_rls_active() is False

    def test_mode_property(self) -> None:
        mgr = RLSPolicyManager(mode=PlacementMode.SHARED_DB)
        assert mgr.mode == PlacementMode.SHARED_DB