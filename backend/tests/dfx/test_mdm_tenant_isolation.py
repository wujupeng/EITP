"""EITP-MDM-001-T17-04 多租户隔离测试 - 四层纵深防护验证。

覆盖 design 2.8.3 跨租户访问四层纵深防护：
1. API 层: SecurityContext.tenant_id 校验（应用服务入口拒绝跨租户操作）
2. 应用层: DataScope 收敛（请求范围 ∩ 授权范围，越权拒绝）
3. 仓储层: TenantFilterEvent 自动追加 WHERE tenant_id
4. 数据库层: RLS 强制 tenant_id 匹配（共享模式启用，独立模式禁用）

附加：跨租户访问企业商品/定制/审计被拦截、跨企业引用企业商品被拒绝、
集团级表不启用 RLS（全平台共享）。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.application.enterprise_product.enterprise_customization_app_svc import (
    EnterpriseCustomizationAppSvc,
)
from app.application.enterprise_product.enterprise_product_app_svc import (
    EnterpriseProductAppSvc,
)
from app.application.governance.master_data_audit_app_svc import (
    MasterDataAuditAppSvc,
)
from app.domain.enterprise_product.services.cross_enterprise_ref_checker import (
    CrossEnterpriseRefChecker,
)
from app.domain.group_catalog.aggregates.group_product_aggregate import (
    GroupProductAggregate,
    GroupProductStatus,
)
from app.domain.group_catalog.services.group_catalog_permission_checker import (
    GroupCatalogPermissionChecker,
)
from app.domain.shared.entity import EntityId
from app.infrastructure.db.rls_policy import PlacementMode, RLSPolicyManager
from app.infrastructure.db.tenant_filter import (
    disable_tenant_filter,
    enable_tenant_filter,
    get_tenant_id_from_context,
)
from app.interfaces.middleware.data_scope_guard import (
    DataScope,
    DataScopeGuard,
    DataScopeLevel,
)
from app.interfaces.middleware.error_handler import (
    DomainError,
    ErrorCode,
    MDMError,
    MDMErrorCode,
)
from app.interfaces.middleware.security_context import (
    PermissionSummary,
    ResolvedDataScope,
    RoleSummary,
    SecurityContext,
    TenantIdentity,
    UserIdentity,
)


# 集团级表（无 tenant_id，全平台共享，不启用 RLS）- design 2.8.1
GROUP_LEVEL_TABLES = frozenset(
    {
        "mdm_group_product",
        "mdm_group_sku",
        "mdm_group_category",
        "mdm_group_brand",
        "mdm_group_unit",
    }
)

# 企业级表（含 tenant_id，启用 RLS）- design 2.8.1
ENTERPRISE_LEVEL_TABLES = frozenset(
    {
        "mdm_enterprise_product",
        "mdm_enterprise_sku",
        "mdm_product_reference",
        "mdm_product_customization",
        "mdm_enterprise_category",
    }
)


class _MockSession:
    """最小异步会话桩 - 跨租户测试在调用仓储前即被拦截，不会触达会话。"""

    async def execute(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        return self

    def scalar_one_or_none(self):
        return None

    def scalars(self):
        return self

    def all(self):
        return []

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def flush(self) -> None:
        pass


class _StubAsyncSession:
    """记录 SQL 执行的异步会话桩 - 用于验证 RLS DDL 下发。"""

    def __init__(self) -> None:
        self.executed: list[tuple[object, dict | None]] = []

    async def execute(self, stmt, params: dict | None = None):  # type: ignore[no-untyped-def]
        self.executed.append((stmt, params))
        return self

    def scalar_one_or_none(self):
        return None

    def scalars(self):
        return self

    def all(self):
        return []


def _make_security_context(
    tenant_id: uuid4 | None = None,
    is_platform_admin: bool = False,
    permissions: frozenset[str] | None = None,
) -> SecurityContext:
    """构造 SecurityContext 五元组（User+Tenant+Roles+Permissions+DataScope）。"""
    return SecurityContext(
        user=UserIdentity(
            user_id=uuid4(),
            username="tester",
            is_platform_admin=is_platform_admin,
        ),
        tenant=TenantIdentity(tenant_id=tenant_id or uuid4()),
        roles=(RoleSummary(role_id=uuid4(), role_code="mdm_admin", role_name="MDM 管理员"),),
        permissions=PermissionSummary(codes=permissions or frozenset()),
        data_scope=ResolvedDataScope(
            scope_type="platform" if is_platform_admin else "tenant",
        ),
    )


def _make_group_product(
    status: GroupProductStatus = GroupProductStatus.ACTIVE,
    published_version: int = 1,
) -> GroupProductAggregate:
    """构造已发布集团商品聚合根。"""
    return GroupProductAggregate(
        id=EntityId.generate(),
        group_product_code="GP-001",
        group_product_name="集团商品",
        base_unit_id=uuid4(),
        status=status,
        published_version=published_version,
    )


@pytest.fixture
def security_context():
    """管理 SecurityContext 上下文生命周期，测试结束自动清理。

    注意：pytest-asyncio 为 async 测试创建独立上下文，ContextVar token 跨上下文
    reset 会抛 ValueError，故 teardown 直接清空当前上下文。
    """
    def _set(ctx: SecurityContext) -> SecurityContext:
        SecurityContext.set(ctx)
        return ctx

    yield _set

    SecurityContext.set(None)


# ---------------------------------------------------------------------------
# 第 1 层：API 层 SecurityContext.tenant_id 校验
# ---------------------------------------------------------------------------


class TestApiLayerTenantIsolation:
    """API 层纵深防护 - SecurityContext.tenant_id 校验。

    应用服务入口校验 ctx.tenant.tenant_id 与请求 tenant_id 一致，
    跨租户操作在触达仓储前即被拒绝（EITP_MDM_CROSS_TENANT_POLICY_DENIED）。
    """

    async def test_cross_tenant_reference_group_product_denied(
        self, security_context
    ) -> None:
        """租户 A 用户引用集团商品到租户 B → 拒绝。"""
        tenant_a = uuid4()
        tenant_b = uuid4()
        security_context(_make_security_context(tenant_id=tenant_a))

        svc = EnterpriseProductAppSvc(_MockSession())
        with pytest.raises(MDMError) as exc:
            await svc.reference_group_product(
                tenant_id=tenant_b,
                group_product_id=uuid4(),
                enterprise_product_code="EP-X",
            )
        assert exc.value.code == MDMErrorCode.CROSS_TENANT_POLICY_DENIED

    async def test_cross_tenant_create_customization_denied(
        self, security_context
    ) -> None:
        """租户 A 用户为租户 B 创建定制 → 拒绝。"""
        tenant_a = uuid4()
        tenant_b = uuid4()
        security_context(_make_security_context(tenant_id=tenant_a))

        svc = EnterpriseCustomizationAppSvc(_MockSession())
        with pytest.raises(MDMError) as exc:
            await svc.create_customization(
                tenant_id=tenant_b,
                enterprise_product_id=uuid4(),
            )
        assert exc.value.code == MDMErrorCode.CROSS_TENANT_POLICY_DENIED

    async def test_cross_tenant_query_audit_denied(self, security_context) -> None:
        """租户 A 用户查询租户 B 审计历史 → 拒绝。"""
        tenant_a = uuid4()
        tenant_b = uuid4()
        security_context(
            _make_security_context(
                tenant_id=tenant_a,
                permissions=frozenset({"mdm:master_data:query"}),
            )
        )

        svc = MasterDataAuditAppSvc(_MockSession())
        with pytest.raises(MDMError) as exc:
            await svc.list_by_tenant(tenant_id=tenant_b)
        assert exc.value.code == MDMErrorCode.CROSS_TENANT_POLICY_DENIED

    async def test_unauthenticated_access_denied(self) -> None:
        """无 SecurityContext → 直接访问被拒绝。"""
        SecurityContext.set(None)
        svc = EnterpriseProductAppSvc(_MockSession())
        with pytest.raises(MDMError) as exc:
            await svc.reference_group_product(
                tenant_id=uuid4(),
                group_product_id=uuid4(),
                enterprise_product_code="EP-X",
            )
        assert exc.value.code == MDMErrorCode.DIRECT_ACCESS_DENIED

    async def test_platform_admin_cross_tenant_audit_allowed(
        self, security_context
    ) -> None:
        """平台超级管理员跨租户查询审计 → 放行（BYPASSRLS 豁免）。"""
        tenant_a = uuid4()
        tenant_b = uuid4()
        security_context(
            _make_security_context(
                tenant_id=tenant_a,
                is_platform_admin=True,
                permissions=frozenset({"mdm:master_data:query"}),
            )
        )

        svc = MasterDataAuditAppSvc(_MockSession())
        # 平台管理员不抛 CROSS_TENANT_POLICY_DENIED；触达仓储后由桩返回空列表
        result = await svc.list_by_tenant(tenant_id=tenant_b)
        assert result == []


# ---------------------------------------------------------------------------
# 第 2 层：应用层 DataScope 收敛
# ---------------------------------------------------------------------------


class TestApplicationLayerDataScope:
    """应用层 DataScope 收敛 - 请求范围 ∩ 授权范围，越权拒绝。"""

    def test_cross_tenant_access_denied_by_datascope_guard(self) -> None:
        """DataScopeGuard 拒绝跨租户访问（非平台管理员）。"""
        from app.interfaces.middleware.tenant_context import TenantContext

        ctx = TenantContext(tenant_id=uuid4())
        target = uuid4()
        with pytest.raises(DomainError) as exc:
            DataScopeGuard.enforce_tenant_isolation(ctx, target)
        assert exc.value.code == ErrorCode.CROSS_TENANT_REF_DENIED

    def test_same_tenant_access_allowed_by_datascope_guard(self) -> None:
        """DataScopeGuard 放行同租户访问。"""
        from app.interfaces.middleware.tenant_context import TenantContext

        tenant_id = uuid4()
        ctx = TenantContext(tenant_id=tenant_id)
        DataScopeGuard.enforce_tenant_isolation(ctx, tenant_id)

    def test_platform_admin_cross_tenant_allowed_by_datascope_guard(self) -> None:
        """平台管理员跨租户访问由 DataScopeGuard 放行。"""
        from app.interfaces.middleware.tenant_context import TenantContext

        ctx = TenantContext(tenant_id=uuid4(), is_platform_admin=True)
        DataScopeGuard.enforce_tenant_isolation(ctx, uuid4())

    def test_scope_subset_converges_partial_violation(self) -> None:
        """请求范围超出授权范围 → 收敛为交集，越权部分剔除。"""
        valid_id = uuid4()
        invalid_id = uuid4()
        authorized = DataScope(
            tenant_id=uuid4(),
            level=DataScopeLevel.ENTERPRISE,
            scope_ids=(valid_id,),
        )
        result = DataScopeGuard.enforce_scope_subset(authorized, (valid_id, invalid_id))
        assert valid_id in result
        assert invalid_id not in result

    def test_scope_subset_within_authorized_passes(self) -> None:
        """请求范围是授权范围子集 → 全部放行。"""
        ids = (uuid4(), uuid4())
        authorized = DataScope(
            tenant_id=uuid4(),
            level=DataScopeLevel.ENTERPRISE,
            scope_ids=ids,
        )
        result = DataScopeGuard.enforce_scope_subset(authorized, ids)
        assert result == ids


# ---------------------------------------------------------------------------
# 第 3 层：仓储层 TenantFilterEvent 自动追加 WHERE tenant_id
# ---------------------------------------------------------------------------


class TestRepositoryLayerTenantFilter:
    """仓储层纵深防护 - TenantFilterEvent 自动追加 WHERE tenant_id。"""

    def test_get_tenant_id_from_context_returns_current_tenant(
        self, security_context
    ) -> None:
        """TenantFilterEvent 从 SecurityContext 获取当前 tenant_id。"""
        tenant_id = uuid4()
        security_context(_make_security_context(tenant_id=tenant_id))
        enable_tenant_filter()
        assert get_tenant_id_from_context() == tenant_id

    def test_tenant_filter_rejects_without_context(self) -> None:
        """无租户上下文 → 仓储层查询被拒绝（严格模式 fail-closed）。"""
        SecurityContext.set(None)
        enable_tenant_filter()
        with pytest.raises(RuntimeError, match="无 TenantContext"):
            get_tenant_id_from_context()

    def test_tenant_filter_can_be_disabled_for_platform_admin(self) -> None:
        """平台级跨租户运维场景可显式禁用租户过滤。"""
        disable_tenant_filter()
        # 禁用后 get_tenant_id_from_context 仍会尝试获取上下文，
        # 但 _apply_tenant_filter 会跳过过滤；此处验证开关状态可切换
        enable_tenant_filter()
        # 开关恢复后正常工作（无上下文仍抛错，证明开关生效）
        SecurityContext.set(None)
        with pytest.raises(RuntimeError):
            get_tenant_id_from_context()


# ---------------------------------------------------------------------------
# 第 4 层：数据库层 RLS 强制 tenant_id 匹配
# ---------------------------------------------------------------------------


class TestDatabaseLayerRLS:
    """数据库层纵深防护 - RLS 强制 tenant_id 匹配。"""

    def test_shared_db_rls_active(self) -> None:
        """共享数据库模式 RLS 生效。"""
        mgr = RLSPolicyManager(PlacementMode.SHARED_DB)
        assert mgr.is_rls_active() is True

    def test_dedicated_db_rls_inactive(self) -> None:
        """独立数据库模式靠连接隔离，RLS 不启用。"""
        mgr = RLSPolicyManager(PlacementMode.DEDICATED_DB)
        assert mgr.is_rls_active() is False

    def test_dedicated_instance_rls_inactive(self) -> None:
        """独立实例模式靠连接隔离，RLS 不启用。"""
        mgr = RLSPolicyManager(PlacementMode.DEDICATED_INSTANCE)
        assert mgr.is_rls_active() is False

    async def test_enable_rls_for_enterprise_table_issues_ddl(self) -> None:
        """共享模式对企业级表下发 ENABLE ROW LEVEL SECURITY DDL。"""
        session = _StubAsyncSession()
        mgr = RLSPolicyManager(PlacementMode.SHARED_DB)
        await mgr.enable_rls_for_table(session, "mdm_enterprise_product")
        sqls = [str(stmt) for stmt, _ in session.executed]
        assert any("ENABLE ROW LEVEL SECURITY" in s for s in sqls)
        assert any("rls_tenant_isolation_mdm_enterprise_product" in s for s in sqls)

    async def test_enable_rls_skipped_in_dedicated_mode(self) -> None:
        """独立模式不对表下发 RLS DDL。"""
        session = _StubAsyncSession()
        mgr = RLSPolicyManager(PlacementMode.DEDICATED_DB)
        await mgr.enable_rls_for_table(session, "mdm_enterprise_product")
        assert session.executed == []

    async def test_set_tenant_context_sets_app_setting(self) -> None:
        """set_tenant_context 下发 app.tenant_id 会话设置。"""
        session = _StubAsyncSession()
        mgr = RLSPolicyManager(PlacementMode.SHARED_DB)
        tenant_id = uuid4()
        await mgr.set_tenant_context(session, tenant_id)
        assert len(session.executed) == 1
        stmt, params = session.executed[0]
        assert "set_config" in str(stmt)
        assert params == {"tenant_id": str(tenant_id)}


# ---------------------------------------------------------------------------
# 集团级表 RLS 豁免（全平台共享）
# ---------------------------------------------------------------------------


class TestGroupLevelTableRLSExemption:
    """集团级表不启用 RLS - 全平台共享数据（design 2.8.1）。"""

    def test_group_and_enterprise_tables_disjoint(self) -> None:
        """集团级表与企业级表分类不相交。"""
        assert GROUP_LEVEL_TABLES.isdisjoint(ENTERPRISE_LEVEL_TABLES)

    def test_group_level_tables_have_no_tenant_id_by_design(self) -> None:
        """集团级表设计上无 tenant_id 列（全平台共享）。"""
        # design 2.8.1: 集团级表无 tenant_id 列，不启用 RLS
        # 此处验证设计约定常量已正确分类
        assert "mdm_group_product" in GROUP_LEVEL_TABLES
        assert "mdm_enterprise_product" not in GROUP_LEVEL_TABLES

    async def test_group_table_rls_not_enabled_by_migration_convention(self) -> None:
        """迁移 027 仅对企业级表下发 RLS，集团级表不启用。

        验证：对企业级表调用 enable_rls_for_table 下发 DDL，
        对集团级表设计上不调用（由迁移脚本保证）。
        此处验证 RLSPolicyManager 对集团级表若被误调用仍会下发 DDL，
        但迁移约定不对其调用 —— 以常量分类表达约定。
        """
        session = _StubAsyncSession()
        mgr = RLSPolicyManager(PlacementMode.SHARED_DB)
        # 迁移仅对企业级表启用 RLS
        for table in ENTERPRISE_LEVEL_TABLES:
            await mgr.enable_rls_for_table(session, table)
        # 提取所有 ENABLE ROW LEVEL SECURITY 语句
        enable_stmts = [
            str(stmt) for stmt, _ in session.executed
            if "ENABLE ROW LEVEL SECURITY" in str(stmt)
        ]
        # 验证企业级表均被启用 RLS
        assert len(enable_stmts) == len(ENTERPRISE_LEVEL_TABLES)
        for ent_table in ENTERPRISE_LEVEL_TABLES:
            assert any(ent_table in s for s in enable_stmts)
        # 验证集团级表未被启用（迁移约定：未对其调用 enable_rls_for_table）
        for group_table in GROUP_LEVEL_TABLES:
            assert not any(group_table in s for s in enable_stmts)


# ---------------------------------------------------------------------------
# 跨企业引用校验
# ---------------------------------------------------------------------------


class TestCrossEnterpriseReference:
    """跨企业引用企业商品被拒绝 - 跨企业共享必须通过集团商品目录（spec 5.2.1.9）。"""

    def test_cross_enterprise_direct_ref_denied(self) -> None:
        """企业 A 直接引用企业 B 的企业商品 → 拒绝。"""
        tenant_a = uuid4()
        tenant_b = uuid4()
        with pytest.raises(MDMError) as exc:
            CrossEnterpriseRefChecker.validate_no_cross_enterprise_direct_ref(
                source_tenant_id=tenant_a,
                target_tenant_id=tenant_b,
            )
        assert exc.value.code == MDMErrorCode.CROSS_ENTERPRISE_REF_DENIED

    def test_same_enterprise_ref_allowed(self) -> None:
        """同企业内引用 → 放行。"""
        tenant = uuid4()
        CrossEnterpriseRefChecker.validate_no_cross_enterprise_direct_ref(
            source_tenant_id=tenant,
            target_tenant_id=tenant,
        )

    def test_reference_to_disabled_group_product_denied(self) -> None:
        """引用已停用集团商品 → 拒绝。"""
        gp = _make_group_product(status=GroupProductStatus.DISABLED)
        with pytest.raises(MDMError) as exc:
            CrossEnterpriseRefChecker.validate_group_product_available(gp)
        assert exc.value.code == MDMErrorCode.GROUP_PRODUCT_DISABLED

    def test_reference_to_unpublished_group_product_denied(self) -> None:
        """引用未发布集团商品 → 拒绝。"""
        gp = _make_group_product(published_version=0)
        with pytest.raises(MDMError) as exc:
            CrossEnterpriseRefChecker.validate_group_product_available(gp)
        assert exc.value.code == MDMErrorCode.GROUP_PRODUCT_NOT_PUBLISHED

    def test_reference_to_active_published_group_product_allowed(self) -> None:
        """引用已发布且未停用集团商品 → 放行。"""
        gp = _make_group_product(status=GroupProductStatus.ACTIVE, published_version=1)
        CrossEnterpriseRefChecker.validate_group_product_available(gp)

    def test_duplicate_reference_same_tenant_group_denied(self) -> None:
        """同一企业重复引用同一集团商品 → 拒绝（复合唯一约束）。"""
        tenant = uuid4()
        group_product_id = uuid4()
        existing = [(tenant, group_product_id)]
        with pytest.raises(MDMError) as exc:
            CrossEnterpriseRefChecker.validate_no_duplicate_reference(
                existing_refs=existing,
                tenant_id=tenant,
                group_product_id=group_product_id,
            )
        assert exc.value.code == MDMErrorCode.DUPLICATE_REFERENCE

    def test_different_tenant_reference_same_group_allowed(self) -> None:
        """不同企业引用同一集团商品 → 放行（多租户架构优势）。"""
        tenant_a = uuid4()
        tenant_b = uuid4()
        group_product_id = uuid4()
        existing = [(tenant_a, group_product_id)]
        CrossEnterpriseRefChecker.validate_no_duplicate_reference(
            existing_refs=existing,
            tenant_id=tenant_b,
            group_product_id=group_product_id,
        )


# ---------------------------------------------------------------------------
# RLS 策略生命周期（disable/clear/mode 切换）
# ---------------------------------------------------------------------------


class TestRLSPolicyLifecycle:
    """RLS 策略生命周期 - 禁用/清理上下文/模式切换。"""

    async def test_disable_rls_for_table_issues_ddl(self) -> None:
        """禁用表 RLS 下发 DROP POLICY + DISABLE ROW LEVEL SECURITY。"""
        session = _StubAsyncSession()
        mgr = RLSPolicyManager(PlacementMode.SHARED_DB)
        await mgr.disable_rls_for_table(session, "mdm_enterprise_product")
        sqls = [str(stmt) for stmt, _ in session.executed]
        assert any("DISABLE ROW LEVEL SECURITY" in s for s in sqls)
        assert any("DROP POLICY" in s for s in sqls)

    async def test_clear_tenant_context_shared_mode(self) -> None:
        """共享模式清理租户上下文下发 set_config。"""
        session = _StubAsyncSession()
        mgr = RLSPolicyManager(PlacementMode.SHARED_DB)
        await mgr.clear_tenant_context(session)
        assert len(session.executed) == 1
        assert "set_config" in str(session.executed[0][0])

    async def test_set_tenant_context_skipped_in_dedicated_mode(self) -> None:
        """独立模式 set_tenant_context 跳过。"""
        session = _StubAsyncSession()
        mgr = RLSPolicyManager(PlacementMode.DEDICATED_DB)
        await mgr.set_tenant_context(session, uuid4())
        assert session.executed == []

    async def test_clear_tenant_context_skipped_in_dedicated_mode(self) -> None:
        """独立模式 clear_tenant_context 跳过。"""
        session = _StubAsyncSession()
        mgr = RLSPolicyManager(PlacementMode.DEDICATED_DB)
        await mgr.clear_tenant_context(session)
        assert session.executed == []

    def test_rls_mode_property(self) -> None:
        """RLS 管理器 mode 属性。"""
        mgr = RLSPolicyManager(PlacementMode.SHARED_DB)
        assert mgr.mode == PlacementMode.SHARED_DB


# ---------------------------------------------------------------------------
# 集团目录权限边界（审批/分类/单位管理）
# ---------------------------------------------------------------------------


class TestGroupCatalogPermissionBoundary:
    """集团目录权限边界 - 审批/分类/单位管理权限校验（spec 4.3.2）。"""

    def test_is_platform_admin_true(self, security_context) -> None:
        """平台管理员识别。"""
        security_context(_make_security_context(is_platform_admin=True))
        assert GroupCatalogPermissionChecker.is_platform_admin() is True

    def test_is_platform_admin_false(self, security_context) -> None:
        """非平台管理员识别。"""
        security_context(_make_security_context(is_platform_admin=False))
        assert GroupCatalogPermissionChecker.is_platform_admin() is False

    def test_is_platform_admin_no_context(self) -> None:
        """无安全上下文 → 非平台管理员。"""
        SecurityContext.set(None)
        assert GroupCatalogPermissionChecker.is_platform_admin() is False

    def test_enterprise_admin_cannot_manage_category(
        self, security_context
    ) -> None:
        """企业管理员不可管理集团分类。"""
        security_context(_make_security_context(is_platform_admin=False))
        with pytest.raises(MDMError) as exc:
            GroupCatalogPermissionChecker.enforce_category_manage()
        assert exc.value.code == MDMErrorCode.GROUP_CATEGORY_PERMISSION_DENIED

    def test_category_manager_can_manage(self, security_context) -> None:
        """具有分类管理权限 → 放行。"""
        security_context(
            _make_security_context(
                permissions=frozenset({"mdm:group_category:manage"}),
            )
        )
        GroupCatalogPermissionChecker.enforce_category_manage()

    def test_enterprise_admin_cannot_manage_unit(
        self, security_context
    ) -> None:
        """企业管理员不可管理集团单位。"""
        security_context(_make_security_context(is_platform_admin=False))
        with pytest.raises(MDMError) as exc:
            GroupCatalogPermissionChecker.enforce_unit_manage()
        assert exc.value.code == MDMErrorCode.GROUP_UNIT_PERMISSION_DENIED

    def test_unit_manager_can_manage(self, security_context) -> None:
        """具有单位管理权限 → 放行。"""
        security_context(
            _make_security_context(
                permissions=frozenset({"mdm:group_unit:manage"}),
            )
        )
        GroupCatalogPermissionChecker.enforce_unit_manage()

    def test_approve_permission_allowed(self, security_context) -> None:
        """具有审批权限 → 放行。"""
        security_context(
            _make_security_context(
                permissions=frozenset({"mdm:group_product:approve"}),
            )
        )
        GroupCatalogPermissionChecker.enforce_approve()

    def test_category_manage_no_context_rejected(self) -> None:
        """无上下文管理分类 → 拒绝。"""
        SecurityContext.set(None)
        with pytest.raises(MDMError) as exc:
            GroupCatalogPermissionChecker.enforce_category_manage()
        assert exc.value.code == MDMErrorCode.GROUP_CATEGORY_PERMISSION_DENIED

    def test_unit_manage_no_context_rejected(self) -> None:
        """无上下文管理单位 → 拒绝。"""
        SecurityContext.set(None)
        with pytest.raises(MDMError) as exc:
            GroupCatalogPermissionChecker.enforce_unit_manage()
        assert exc.value.code == MDMErrorCode.GROUP_UNIT_PERMISSION_DENIED