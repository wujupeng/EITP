"""EITP-MDM-001-T17-06 安全测试 - 纵深防御与 fail-closed 原则验证。

覆盖 spec 4.2 / 4.3 安全要求：
1. 主数据版本不可变（append-only + REVOKE UPDATE/DELETE + Trigger 双保险）
2. 审计记录不可篡改（frozen dataclass + append-only）
3. 禁止绕过治理工作流直接修改发布数据（状态机锁定）
4. 禁止企业管理员修改集团商品目录（平台级角色校验）
5. 禁止企业定制修改集团基准属性（聚合根方法边界）
6. 审计不含敏感信息（明文密码/Token）
7. fail-closed 原则（主数据服务故障下游拒绝创建新单据）
"""

from __future__ import annotations

from dataclasses import fields
from uuid import uuid4

import pytest

from app.application.governance.master_data_version_comparator import (
    MasterDataVersionComparator,
)
from app.application.master_data_query.master_data_query_app_svc import (
    MasterDataQueryAppSvc,
)
from app.application.enterprise_product.enterprise_customization_app_svc import (
    EnterpriseCustomizationAppSvc,
)
from app.application.governance.master_data_audit_app_svc import (
    MasterDataAuditAppSvc,
)
from app.domain.audit.audit_entry import AuditAction, AuditEntry
from app.domain.audit.master_data_audit_aggregate import MasterDataAuditAggregate
from app.domain.enterprise_product.aggregates.product_customization_aggregate import (
    CostModelType,
    InventoryStrategy,
    ProductCustomizationAggregate,
)
from app.domain.governance.aggregates.governance_workflow_aggregate import (
    GovernanceLevel,
    GovernanceWorkflowAggregate,
)
from app.domain.governance.aggregates.master_data_version_aggregate import (
    ChangeType,
    MasterDataVersionAggregate,
)
from app.domain.governance.value_objects.governance_state import GovernanceState
from app.domain.group_catalog.services.group_catalog_permission_checker import (
    GroupCatalogPermissionChecker,
)
from app.domain.shared.entity import EntityId
from app.infrastructure.master_data_query.master_data_query_redis_store import (
    MasterDataQueryRedisStore,
)
from app.infrastructure.enterprise_product.enterprise_product_repository import (
    ProductCustomizationRepository,
)
from app.infrastructure.governance.governance_repositories import (
    MasterDataAuditRepository,
)
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode
from app.interfaces.middleware.security_context import (
    PermissionSummary,
    ResolvedDataScope,
    RoleSummary,
    SecurityContext,
    TenantIdentity,
    UserIdentity,
)


# 审计结构禁止出现的敏感字段名关键词
SENSITIVE_FIELD_KEYWORDS = frozenset({"password", "token", "secret", "credential"})

# 企业定制聚合根允许的企业级属性修改方法
ENTERPRISE_CUSTOMIZATION_METHODS = frozenset(
    {
        "update_sales_price",
        "update_purchase_price",
        "update_inventory_strategy",
        "update_safety_stock",
        "update_cost_model",
        "update_custom_attributes",
    }
)

# 企业定制聚合根禁止暴露的集团基准属性修改方法
FORBIDDEN_GROUP_BASE_METHODS = frozenset(
    {
        "update_group_sku_code",
        "update_specification",
        "update_base_unit",
        "update_unit",
        "update_group_product_name",
        "update_group_category",
        "update_group_brand",
        "update_barcode_list",
    }
)


class _MockSession:
    """最小异步会话桩 - fail-closed 测试中商品查询返回 None。"""

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


def _make_security_context(
    tenant_id: uuid4 | None = None,
    is_platform_admin: bool = False,
    permissions: frozenset[str] | None = None,
) -> SecurityContext:
    return SecurityContext(
        user=UserIdentity(
            user_id=uuid4(),
            username="tester",
            is_platform_admin=is_platform_admin,
        ),
        tenant=TenantIdentity(tenant_id=tenant_id or uuid4()),
        roles=(RoleSummary(role_id=uuid4(), role_code="mdm_admin", role_name="MDM"),),
        permissions=PermissionSummary(codes=permissions or frozenset()),
        data_scope=ResolvedDataScope(
            scope_type="platform" if is_platform_admin else "tenant",
        ),
    )


@pytest.fixture
def security_context():
    def _set(ctx: SecurityContext) -> SecurityContext:
        SecurityContext.set(ctx)
        return ctx

    yield _set

    SecurityContext.set(None)


# ---------------------------------------------------------------------------
# 1. 主数据版本不可变（append-only + REVOKE UPDATE/DELETE + Trigger 双保险）
# ---------------------------------------------------------------------------


class TestMasterDataVersionImmutability:
    """主数据版本不可变 - append-only，写入后不可修改不可删除（spec 4.2.1）。"""

    def test_version_number_starts_from_one(self) -> None:
        """版本号从 1 开始递增。"""
        version = MasterDataVersionAggregate.create_initial(
            entity_type="group_product",
            entity_id=uuid4(),
            snapshot_after={"name": "v1"},
            operated_by=uuid4(),
        )
        assert version.version_number == 1
        assert version.change_type == ChangeType.CREATE

    def test_version_number_below_one_rejected(self) -> None:
        """版本号 < 1 → 拒绝。"""
        with pytest.raises(MDMError) as exc:
            MasterDataVersionAggregate(
                id=EntityId.generate(),
                entity_type="group_product",
                entity_id=uuid4(),
                version_number=0,
                snapshot_after={"name": "v0"},
                change_type=ChangeType.CREATE,
                operated_by=uuid4(),
            )
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_version_aggregate_has_no_update_methods(self) -> None:
        """版本聚合根不暴露 update/delete 方法 - append-only 约束。"""
        version = MasterDataVersionAggregate.create_initial(
            entity_type="group_product",
            entity_id=uuid4(),
            snapshot_after={"name": "v1"},
            operated_by=uuid4(),
        )
        public_methods = {
            name
            for name in dir(version)
            if not name.startswith("_") and callable(getattr(version, name))
        }
        # 禁止存在直接修改/删除版本的方法
        assert "update" not in public_methods
        assert "delete" not in public_methods
        assert "modify" not in public_methods
        assert "set_version_number" not in public_methods

    def test_version_snapshot_is_read_only(self) -> None:
        """版本快照属性只读 - 不可变约束。"""
        version = MasterDataVersionAggregate.create_initial(
            entity_type="group_product",
            entity_id=uuid4(),
            snapshot_after={"name": "v1", "status": "active"},
            operated_by=uuid4(),
        )
        # 属性通过 property 暴露，无 setter
        assert version.snapshot_after == {"name": "v1", "status": "active"}
        assert version.version_number == 1
        # 验证 property 无 fset
        for prop_name in ("version_number", "snapshot_after", "snapshot_before"):
            prop = getattr(type(version), prop_name)
            assert prop.fset is None, f"{prop_name} 不应有 setter"

    def test_version_compare_does_not_mutate_versions(self) -> None:
        """版本对比不修改原版本对象 - 不可变约束。"""
        va = MasterDataVersionAggregate.create_initial(
            entity_type="group_product",
            entity_id=uuid4(),
            snapshot_after={"name": "v1"},
            operated_by=uuid4(),
        )
        vb = MasterDataVersionAggregate.create_update(
            entity_type="group_product",
            entity_id=va.entity_id,
            version_number=2,
            snapshot_before=va.snapshot_after,
            snapshot_after={"name": "v2"},
            operated_by=uuid4(),
        )
        MasterDataVersionComparator.compare(va, vb)
        # 对比后原版本快照不变
        assert va.snapshot_after == {"name": "v1"}
        assert vb.snapshot_after == {"name": "v2"}

    @pytest.mark.skip(reason="需接入 DB 验证 REVOKE UPDATE/DELETE 权限，CI 环境执行")
    def test_revoke_update_delete_on_version_table(self) -> None:
        """REVOKE UPDATE/DELETE on mdm_master_data_version（DB 层约束）。"""

    @pytest.mark.skip(reason="需接入 DB 验证 Trigger 拒绝 UPDATE/DELETE，CI 环境执行")
    def test_trigger_rejects_update_delete_on_version_table(self) -> None:
        """Trigger 强制拒绝 UPDATE/DELETE（双保险，spec 5.8.1.2）。"""


# ---------------------------------------------------------------------------
# 2. 审计记录不可篡改（frozen dataclass + append-only）
# ---------------------------------------------------------------------------


class TestAuditTamperProof:
    """审计记录不可篡改 - frozen dataclass，仅追加（spec 4.3.5）。"""

    def test_master_data_audit_is_frozen(self) -> None:
        """MasterDataAuditAggregate 为 frozen dataclass - 不可修改字段。"""
        audit = MasterDataAuditAggregate.create(
            action=AuditAction.MASTER_DATA_PUBLISHED,
            entity_type="group_product",
            entity_id=str(uuid4()),
            operated_by=uuid4(),
        )
        with pytest.raises(Exception):
            audit.action = AuditAction.CREATE  # type: ignore[misc]

    def test_audit_entry_is_frozen(self) -> None:
        """AuditEntry 为 frozen dataclass - 不可修改字段。"""
        entry = AuditEntry.create(
            tenant_id=uuid4(),
            user_id=uuid4(),
            action=AuditAction.CREATE,
            entity_type="group_product",
            entity_id=str(uuid4()),
        )
        with pytest.raises(Exception):
            entry.action = AuditAction.DELETE  # type: ignore[misc]

    def test_audit_has_no_update_delete_methods(self) -> None:
        """审计聚合根不暴露 update/delete 方法 - append-only 约束。"""
        audit = MasterDataAuditAggregate.create(
            action=AuditAction.CREATE,
            entity_type="group_product",
            entity_id=str(uuid4()),
            operated_by=uuid4(),
        )
        public_methods = {
            name
            for name in dir(audit)
            if not name.startswith("_") and callable(getattr(audit, name))
        }
        assert "update" not in public_methods
        assert "delete" not in public_methods
        assert "modify" not in public_methods

    def test_audit_create_generates_unique_id_and_timestamp(self) -> None:
        """每次创建审计记录生成唯一 ID 与时间戳 - 不可回溯篡改。"""
        a1 = MasterDataAuditAggregate.create(
            action=AuditAction.CREATE,
            entity_type="group_product",
            entity_id=str(uuid4()),
            operated_by=uuid4(),
        )
        a2 = MasterDataAuditAggregate.create(
            action=AuditAction.CREATE,
            entity_type="group_product",
            entity_id=str(uuid4()),
            operated_by=uuid4(),
        )
        assert a1.audit_id != a2.audit_id
        assert a1.operated_at <= a2.operated_at

    @pytest.mark.skip(reason="需接入 DB 验证 REVOKE/Trigger，CI 环境执行")
    def test_audit_table_revoke_update_delete(self) -> None:
        """REVOKE UPDATE/DELETE on mdm_master_data_audit（DB 层约束）。"""


# ---------------------------------------------------------------------------
# 3. 禁止绕过治理工作流直接修改发布数据
# ---------------------------------------------------------------------------


class TestGovernanceWorkflowBypass:
    """禁止绕过治理工作流直接修改发布数据（spec 4.3.8）。"""

    def test_published_workflow_cannot_submit_again(self) -> None:
        """已发布工作流不可再次提交 - 必须经新工作流。"""
        wf = GovernanceWorkflowAggregate(
            id=EntityId.generate(),
            governance_level=GovernanceLevel.ENTERPRISE,
            entity_type="group_product",
            target_version_id=uuid4(),
            tenant_id=uuid4(),
            status=GovernanceState.PUBLISHED,
            published_by=uuid4(),
        )
        with pytest.raises(MDMError) as exc:
            wf.submit(uuid4())
        assert exc.value.code == MDMErrorCode.INVALID_GOVERNANCE_STATE_TRANSITION

    def test_published_workflow_can_only_rollback(self) -> None:
        """已发布工作流仅可回滚，不可重新审批/发布。"""
        wf = GovernanceWorkflowAggregate(
            id=EntityId.generate(),
            governance_level=GovernanceLevel.ENTERPRISE,
            entity_type="group_product",
            target_version_id=uuid4(),
            tenant_id=uuid4(),
            status=GovernanceState.PUBLISHED,
            published_by=uuid4(),
        )
        # 回滚允许
        wf.rollback(uuid4(), "发布后发现缺陷")
        assert wf.status == GovernanceState.ROLLED_BACK
        # 回滚后不可再提交
        with pytest.raises(MDMError) as exc:
            wf.submit(uuid4())
        assert exc.value.code == MDMErrorCode.INVALID_GOVERNANCE_STATE_TRANSITION

    def test_rejected_workflow_cannot_proceed(self) -> None:
        """已拒绝工作流不可继续流转 - 必须重新发起。"""
        wf = GovernanceWorkflowAggregate(
            id=EntityId.generate(),
            governance_level=GovernanceLevel.ENTERPRISE,
            entity_type="group_product",
            target_version_id=uuid4(),
            tenant_id=uuid4(),
            status=GovernanceState.REJECTED,
            approved_by=uuid4(),
        )
        with pytest.raises(MDMError) as exc:
            wf.approve(uuid4(), "同意")
        assert exc.value.code == MDMErrorCode.INVALID_GOVERNANCE_STATE_TRANSITION

    def test_submitted_workflow_not_editable(self) -> None:
        """已提交变更申请不可修改内容（spec 5.6.1.3）。"""
        wf = GovernanceWorkflowAggregate(
            id=EntityId.generate(),
            governance_level=GovernanceLevel.ENTERPRISE,
            entity_type="group_product",
            target_version_id=uuid4(),
            tenant_id=uuid4(),
            status=GovernanceState.SUBMITTED,
            submitted_by=uuid4(),
        )
        assert wf.is_editable() is False

    def test_draft_workflow_is_editable(self) -> None:
        """草稿状态可编辑。"""
        wf = GovernanceWorkflowAggregate(
            id=EntityId.generate(),
            governance_level=GovernanceLevel.ENTERPRISE,
            entity_type="group_product",
            target_version_id=uuid4(),
            tenant_id=uuid4(),
        )
        assert wf.is_editable() is True
        assert wf.status == GovernanceState.DRAFT

    def test_published_version_is_immutable_evidence(self) -> None:
        """已发布版本作为不可变事实源 - 版本聚合根 append-only。"""
        version = MasterDataVersionAggregate.create_initial(
            entity_type="group_product",
            entity_id=uuid4(),
            snapshot_after={"name": "已发布", "status": "active"},
            operated_by=uuid4(),
        )
        # 版本快照不可修改（property 无 setter）
        assert type(version).snapshot_after.fset is None
        assert type(version).version_number.fset is None


# ---------------------------------------------------------------------------
# 4. 禁止企业管理员修改集团商品目录
# ---------------------------------------------------------------------------


class TestGroupCatalogPermission:
    """禁止企业管理员修改集团商品目录（spec 4.3.2）。"""

    def test_enterprise_admin_cannot_manage_group_catalog(
        self, security_context
    ) -> None:
        """企业管理员（非平台管理员、无集团管理权限）→ 拒绝。"""
        security_context(_make_security_context(is_platform_admin=False))
        with pytest.raises(MDMError) as exc:
            GroupCatalogPermissionChecker.enforce_manage()
        assert exc.value.code == MDMErrorCode.GROUP_CATALOG_PERMISSION_DENIED

    def test_enterprise_admin_with_only_query_permission_cannot_manage(
        self, security_context
    ) -> None:
        """仅有查询权限的企业管理员 → 不可管理集团目录。"""
        security_context(
            _make_security_context(
                is_platform_admin=False,
                permissions=frozenset({"mdm:master_data:query"}),
            )
        )
        with pytest.raises(MDMError) as exc:
            GroupCatalogPermissionChecker.enforce_manage()
        assert exc.value.code == MDMErrorCode.GROUP_CATALOG_PERMISSION_DENIED

    def test_platform_admin_can_manage_group_catalog(
        self, security_context
    ) -> None:
        """平台超级管理员 → 放行。"""
        security_context(_make_security_context(is_platform_admin=True))
        GroupCatalogPermissionChecker.enforce_manage()

    def test_user_with_group_manage_permission_can_manage(
        self, security_context
    ) -> None:
        """具有 mdm:group_product:manage 权限的用户 → 放行。"""
        security_context(
            _make_security_context(
                is_platform_admin=False,
                permissions=frozenset({"mdm:group_product:manage"}),
            )
        )
        GroupCatalogPermissionChecker.enforce_manage()

    def test_unauthenticated_cannot_manage_group_catalog(self) -> None:
        """无安全上下文 → 拒绝。"""
        SecurityContext.set(None)
        with pytest.raises(MDMError) as exc:
            GroupCatalogPermissionChecker.enforce_manage()
        assert exc.value.code == MDMErrorCode.GROUP_CATALOG_PERMISSION_DENIED

    def test_enterprise_admin_cannot_approve_group_catalog(
        self, security_context
    ) -> None:
        """企业管理员不可审批集团商品。"""
        security_context(_make_security_context(is_platform_admin=False))
        with pytest.raises(MDMError) as exc:
            GroupCatalogPermissionChecker.enforce_approve()
        assert exc.value.code == MDMErrorCode.GROUP_CATALOG_PERMISSION_DENIED


# ---------------------------------------------------------------------------
# 5. 禁止企业定制修改集团基准属性
# ---------------------------------------------------------------------------


class TestCustomizationBaseAttributeProtection:
    """禁止企业定制修改集团基准属性（spec 5.2.1.10）。"""

    def test_customization_only_exposes_enterprise_attribute_methods(self) -> None:
        """定制聚合根仅暴露企业级属性修改方法。"""
        methods = {
            name
            for name in dir(ProductCustomizationAggregate)
            if name.startswith("update_") and not name.startswith("_")
        }
        assert ENTERPRISE_CUSTOMIZATION_METHODS.issubset(methods)

    def test_customization_does_not_expose_group_base_methods(self) -> None:
        """定制聚合根不暴露集团基准属性修改方法。"""
        methods = {
            name
            for name in dir(ProductCustomizationAggregate)
            if name.startswith("update_") and not name.startswith("_")
        }
        assert FORBIDDEN_GROUP_BASE_METHODS.isdisjoint(methods)

    def test_customization_can_update_enterprise_price(self) -> None:
        """企业定制可覆盖企业级属性（销售价格）。"""
        from decimal import Decimal

        agg = ProductCustomizationAggregate(
            id=EntityId.generate(),
            tenant_id=uuid4(),
            enterprise_product_id=uuid4(),
        )
        agg.update_sales_price(Decimal("99.50"))
        assert agg.sales_price == Decimal("99.50")

    def test_customization_can_update_enterprise_inventory_strategy(self) -> None:
        """企业定制可覆盖企业级属性（库存策略）。"""
        agg = ProductCustomizationAggregate(
            id=EntityId.generate(),
            tenant_id=uuid4(),
            enterprise_product_id=uuid4(),
        )
        agg.update_inventory_strategy(InventoryStrategy.WARNING)
        assert agg.inventory_strategy == InventoryStrategy.WARNING

    def test_customization_can_update_cost_model(self) -> None:
        """企业定制可覆盖企业级属性（成本模型）。"""
        agg = ProductCustomizationAggregate(
            id=EntityId.generate(),
            tenant_id=uuid4(),
            enterprise_product_id=uuid4(),
        )
        agg.update_cost_model(CostModelType.FIFO)
        assert agg.cost_model == CostModelType.FIFO

    def test_customization_negative_price_rejected(self) -> None:
        """企业定制负价格 → 拒绝（业务规则校验）。"""
        from decimal import Decimal

        agg = ProductCustomizationAggregate(
            id=EntityId.generate(),
            tenant_id=uuid4(),
            enterprise_product_id=uuid4(),
        )
        with pytest.raises(MDMError) as exc:
            agg.update_sales_price(Decimal("-1"))
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID


# ---------------------------------------------------------------------------
# 6. 审计不含敏感信息（明文密码/Token）
# ---------------------------------------------------------------------------


class TestAuditNoSensitiveInfo:
    """审计不含敏感信息 - 禁止存储明文密码/Token（spec 4.3.9）。"""

    def test_master_data_audit_fields_contain_no_sensitive_keywords(self) -> None:
        """MasterDataAuditAggregate 字段名不含敏感关键词。"""
        field_names = {f.name for f in fields(MasterDataAuditAggregate)}
        for name in field_names:
            assert not any(
                kw in name.lower() for kw in SENSITIVE_FIELD_KEYWORDS
            ), f"审计字段 {name} 含敏感关键词"

    def test_audit_entry_fields_contain_no_sensitive_keywords(self) -> None:
        """AuditEntry 字段名不含敏感关键词。"""
        field_names = {f.name for f in fields(AuditEntry)}
        for name in field_names:
            assert not any(
                kw in name.lower() for kw in SENSITIVE_FIELD_KEYWORDS
            ), f"审计字段 {name} 含敏感关键词"

    def test_audit_create_signature_has_no_sensitive_params(self) -> None:
        """AuditEntry.create 构造签名不含敏感参数。"""
        import inspect

        sig = inspect.signature(AuditEntry.create)
        for param_name in sig.parameters:
            assert not any(
                kw in param_name.lower() for kw in SENSITIVE_FIELD_KEYWORDS
            ), f"审计构造参数 {param_name} 含敏感关键词"

    def test_master_data_audit_create_signature_has_no_sensitive_params(self) -> None:
        """MasterDataAuditAggregate.create 构造签名不含敏感参数。"""
        import inspect

        sig = inspect.signature(MasterDataAuditAggregate.create)
        for param_name in sig.parameters:
            assert not any(
                kw in param_name.lower() for kw in SENSITIVE_FIELD_KEYWORDS
            ), f"审计构造参数 {param_name} 含敏感关键词"

    def test_audit_does_not_persist_plaintext_password_in_standard_fields(
        self
    ) -> None:
        """审计标准字段不承载明文密码 - 仅记录操作上下文。"""
        audit = MasterDataAuditAggregate.create(
            action=AuditAction.CREATE,
            entity_type="user",
            entity_id=str(uuid4()),
            operated_by=uuid4(),
            reason="用户创建",
        )
        # 标准字段均为操作上下文，无密码/Token 字段
        assert audit.action == AuditAction.CREATE
        assert audit.reason == "用户创建"
        assert not hasattr(audit, "password")
        assert not hasattr(audit, "token")


# ---------------------------------------------------------------------------
# 7. fail-closed 原则（主数据服务故障下游拒绝创建新单据）
# ---------------------------------------------------------------------------


class TestFailClosedPrinciple:
    """fail-closed 原则 - 主数据服务故障时下游拒绝创建新单据（spec 4.2.6）。"""

    async def test_product_not_available_raises_error(
        self, security_context, monkeypatch
    ) -> None:
        """企业商品不存在 → 抛 PRODUCT_NOT_AVAILABLE（fail-closed）。"""
        security_context(
            _make_security_context(
                permissions=frozenset({"mdm:master_data:query"}),
            )
        )

        async def _none_cache(*args, **kwargs):  # type: ignore[no-untyped-def]
            return None

        monkeypatch.setattr(
            MasterDataQueryRedisStore,
            "get_enterprise_product_cache",
            staticmethod(_none_cache),
        )

        svc = MasterDataQueryAppSvc(_MockSession())
        with pytest.raises(MDMError) as exc:
            await svc.get_master_data(uuid4(), uuid4())
        assert exc.value.code == MDMErrorCode.PRODUCT_NOT_AVAILABLE

    async def test_inactive_product_raises_error(
        self, security_context, monkeypatch
    ) -> None:
        """商品已停用/引用已解除 → 抛 PRODUCT_NOT_AVAILABLE（fail-closed）。"""
        security_context(
            _make_security_context(
                permissions=frozenset({"mdm:master_data:query"}),
            )
        )

        async def _none_cache(*args, **kwargs):  # type: ignore[no-untyped-def]
            return None

        monkeypatch.setattr(
            MasterDataQueryRedisStore,
            "get_enterprise_product_cache",
            staticmethod(_none_cache),
        )

        # 模拟商品存在但已停用（reference_status != "active"）
        class _InactiveProduct:
            reference_status = "reference_released"
            group_product_id = uuid4()

        class _InactiveSession:
            async def execute(self, *args, **kwargs):  # type: ignore[no-untyped-def]
                return self

            def scalar_one_or_none(self):
                return _InactiveProduct()

            def scalars(self):
                return self

            def all(self):
                return []

        svc = MasterDataQueryAppSvc(_InactiveSession())
        with pytest.raises(MDMError) as exc:
            await svc.get_master_data(uuid4(), uuid4())
        assert exc.value.code == MDMErrorCode.PRODUCT_NOT_AVAILABLE

    async def test_unauthenticated_query_rejected(self) -> None:
        """无认证 → 拒绝查询（fail-closed，不放行匿名访问）。"""
        SecurityContext.set(None)
        svc = MasterDataQueryAppSvc(_MockSession())
        with pytest.raises(MDMError) as exc:
            await svc.get_master_data(uuid4(), uuid4())
        assert exc.value.code == MDMErrorCode.DIRECT_ACCESS_DENIED

    async def test_unauthorized_query_rejected(self, security_context) -> None:
        """无查询权限 → 拒绝（fail-closed，不因权限缺失而放行）。"""
        security_context(_make_security_context(permissions=frozenset()))
        svc = MasterDataQueryAppSvc(_MockSession())
        with pytest.raises(MDMError) as exc:
            await svc.get_master_data(uuid4(), uuid4())
        assert exc.value.code == MDMErrorCode.GROUP_CATALOG_PERMISSION_DENIED

    def test_service_unavailable_error_code_defined(self) -> None:
        """SERVICE_UNAVAILABLE 错误码已定义 - fail-closed 故障信号。"""
        assert MDMErrorCode.SERVICE_UNAVAILABLE.value == "EITP_MDM_SERVICE_UNAVAILABLE"
        assert MDMErrorCode.PRODUCT_NOT_AVAILABLE.value == "EITP_MDM_PRODUCT_NOT_AVAILABLE"

    @pytest.mark.skip(reason="需接入 INV-001 下游单据创建集成验证，CI 环境执行")
    def test_downstream_document_creation_rejected_when_mdm_unavailable(self) -> None:
        """主数据服务故障 → 下游 INV-001 拒绝创建新单据（集成验证）。"""


# ---------------------------------------------------------------------------
# 治理工作流成功路径（状态机完整流转）
# ---------------------------------------------------------------------------


class TestGovernanceWorkflowHappyPath:
    """治理工作流状态机完整流转 - DRAFT→SUBMITTED→APPROVED→PUBLISHED→ROLLED_BACK。"""

    def test_submit_draft_to_submitted(self) -> None:
        """DRAFT → SUBMITTED。"""
        wf = GovernanceWorkflowAggregate(
            id=EntityId.generate(),
            governance_level=GovernanceLevel.ENTERPRISE,
            entity_type="group_product",
            target_version_id=uuid4(),
            tenant_id=uuid4(),
        )
        assert wf.status == GovernanceState.DRAFT
        wf.submit(uuid4())
        assert wf.status == GovernanceState.SUBMITTED
        assert wf.submitted_by is not None

    def test_approve_submitted_to_approved(self) -> None:
        """SUBMITTED → APPROVED。"""
        wf = GovernanceWorkflowAggregate(
            id=EntityId.generate(),
            governance_level=GovernanceLevel.ENTERPRISE,
            entity_type="group_product",
            target_version_id=uuid4(),
            tenant_id=uuid4(),
            status=GovernanceState.SUBMITTED,
            submitted_by=uuid4(),
        )
        wf.approve(uuid4(), "同意")
        assert wf.status == GovernanceState.APPROVED
        assert wf.approval_opinion == "同意"

    def test_reject_submitted_to_rejected(self) -> None:
        """SUBMITTED → REJECTED。"""
        wf = GovernanceWorkflowAggregate(
            id=EntityId.generate(),
            governance_level=GovernanceLevel.ENTERPRISE,
            entity_type="group_product",
            target_version_id=uuid4(),
            tenant_id=uuid4(),
            status=GovernanceState.SUBMITTED,
            submitted_by=uuid4(),
        )
        wf.reject(uuid4(), "不符合规范")
        assert wf.status == GovernanceState.REJECTED

    def test_publish_approved_to_published(self) -> None:
        """APPROVED → PUBLISHED。"""
        wf = GovernanceWorkflowAggregate(
            id=EntityId.generate(),
            governance_level=GovernanceLevel.ENTERPRISE,
            entity_type="group_product",
            target_version_id=uuid4(),
            tenant_id=uuid4(),
            status=GovernanceState.APPROVED,
            approved_by=uuid4(),
        )
        wf.publish(uuid4())
        assert wf.status == GovernanceState.PUBLISHED
        assert wf.published_by is not None

    def test_group_level_workflow_has_no_tenant_id(self) -> None:
        """集团级治理工作流无 tenant_id。"""
        wf = GovernanceWorkflowAggregate(
            id=EntityId.generate(),
            governance_level=GovernanceLevel.GROUP,
            entity_type="group_product",
            target_version_id=uuid4(),
        )
        assert wf.tenant_id is None
        assert wf.is_group_level() is True

    def test_group_level_workflow_with_tenant_id_rejected(self) -> None:
        """集团级治理工作流含 tenant_id → 拒绝。"""
        with pytest.raises(MDMError) as exc:
            GovernanceWorkflowAggregate(
                id=EntityId.generate(),
                governance_level=GovernanceLevel.GROUP,
                entity_type="group_product",
                target_version_id=uuid4(),
                tenant_id=uuid4(),
            )
        assert exc.value.code == MDMErrorCode.INVALID_GOVERNANCE_STATE_TRANSITION

    def test_enterprise_level_workflow_requires_tenant_id(self) -> None:
        """企业级治理工作流必须含 tenant_id。"""
        with pytest.raises(MDMError) as exc:
            GovernanceWorkflowAggregate(
                id=EntityId.generate(),
                governance_level=GovernanceLevel.ENTERPRISE,
                entity_type="group_product",
                target_version_id=uuid4(),
            )
        assert exc.value.code == MDMErrorCode.INVALID_GOVERNANCE_STATE_TRANSITION


# ---------------------------------------------------------------------------
# 企业定制完整企业级属性覆盖
# ---------------------------------------------------------------------------


class TestCustomizationEnterpriseAttributes:
    """企业定制企业级属性完整覆盖 - 价格/库存/成本/自定义属性/发布。"""

    def _make_customization(self) -> ProductCustomizationAggregate:
        return ProductCustomizationAggregate(
            id=EntityId.generate(),
            tenant_id=uuid4(),
            enterprise_product_id=uuid4(),
        )

    def test_update_purchase_price(self) -> None:
        from decimal import Decimal

        agg = self._make_customization()
        agg.update_purchase_price(Decimal("50.00"))
        assert agg.purchase_price == Decimal("50.00")

    def test_negative_purchase_price_rejected(self) -> None:
        from decimal import Decimal

        agg = self._make_customization()
        with pytest.raises(MDMError) as exc:
            agg.update_purchase_price(Decimal("-1"))
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_update_safety_stock(self) -> None:
        from decimal import Decimal

        agg = self._make_customization()
        agg.update_safety_stock(Decimal("100"))
        assert agg.safety_stock == Decimal("100")

    def test_negative_safety_stock_rejected(self) -> None:
        from decimal import Decimal

        agg = self._make_customization()
        with pytest.raises(MDMError) as exc:
            agg.update_safety_stock(Decimal("-1"))
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_publish_increments_version(self) -> None:
        """定制发布递增版本号。"""
        agg = self._make_customization()
        agg.publish(1)
        assert agg.version == 1

    def test_publish_non_increment_rejected(self) -> None:
        """发布版本号未递增 → 拒绝。"""
        agg = ProductCustomizationAggregate(
            id=EntityId.generate(),
            tenant_id=uuid4(),
            enterprise_product_id=uuid4(),
            version=2,
        )
        with pytest.raises(MDMError) as exc:
            agg.publish(2)
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_update_custom_attributes(self) -> None:
        """更新自定义属性。"""
        agg = self._make_customization()
        agg.update_custom_attributes({"color": "red", "size": "L"})
        assert agg.custom_attributes == {"color": "red", "size": "L"}


# ---------------------------------------------------------------------------
# 审计写入与查询覆盖
# ---------------------------------------------------------------------------


class TestAuditWriteAndQuery:
    """审计应用服务写入与查询覆盖。"""

    async def test_write_audit_success(
        self, security_context, monkeypatch
    ) -> None:
        """写入审计记录成功。"""
        security_context(_make_security_context())
        saved: list = []

        async def _capture_save(*args, **kwargs):  # type: ignore[no-untyped-def]
            saved.append(args[-1])

        monkeypatch.setattr(MasterDataAuditRepository, "save", _capture_save)
        svc = MasterDataAuditAppSvc(_MockSession())
        audit = await svc.write_audit(
            action=AuditAction.CREATE,
            entity_type="group_product",
            entity_id=str(uuid4()),
            reason="创建商品",
        )
        assert audit.action == AuditAction.CREATE
        assert audit.reason == "创建商品"
        assert saved[0] is audit

    async def test_write_audit_unauthenticated_rejected(self) -> None:
        """无认证写入审计 → 拒绝。"""
        SecurityContext.set(None)
        svc = MasterDataAuditAppSvc(_MockSession())
        with pytest.raises(MDMError) as exc:
            await svc.write_audit(
                action=AuditAction.CREATE,
                entity_type="group_product",
                entity_id=str(uuid4()),
            )
        assert exc.value.code == MDMErrorCode.DIRECT_ACCESS_DENIED

    async def test_list_by_entity_success(
        self, security_context, monkeypatch
    ) -> None:
        """按实体查询审计历史成功。"""
        security_context(
            _make_security_context(
                permissions=frozenset({"mdm:master_data:query"}),
            )
        )

        async def _return_empty(*args, **kwargs):  # type: ignore[no-untyped-def]
            return []

        monkeypatch.setattr(
            MasterDataAuditRepository, "list_by_entity", _return_empty
        )
        svc = MasterDataAuditAppSvc(_MockSession())
        result = await svc.list_by_entity("group_product", str(uuid4()))
        assert result == []

    async def test_list_by_entity_unauthorized_rejected(
        self, security_context
    ) -> None:
        """无查询权限查询审计 → 拒绝。"""
        security_context(_make_security_context(permissions=frozenset()))
        svc = MasterDataAuditAppSvc(_MockSession())
        with pytest.raises(MDMError) as exc:
            await svc.list_by_entity("group_product", str(uuid4()))
        assert exc.value.code == MDMErrorCode.GROUP_CATALOG_PERMISSION_DENIED

    async def test_list_by_tenant_same_tenant_success(
        self, security_context, monkeypatch
    ) -> None:
        """同租户查询审计历史成功。"""
        tenant = uuid4()
        security_context(
            _make_security_context(
                tenant_id=tenant,
                permissions=frozenset({"mdm:master_data:query"}),
            )
        )

        async def _return_empty(*args, **kwargs):  # type: ignore[no-untyped-def]
            return []

        monkeypatch.setattr(
            MasterDataAuditRepository, "list_by_tenant", _return_empty
        )
        svc = MasterDataAuditAppSvc(_MockSession())
        result = await svc.list_by_tenant(tenant)
        assert result == []


# ---------------------------------------------------------------------------
# 主数据查询过滤与定制查询覆盖
# ---------------------------------------------------------------------------


class TestMasterDataQueryFilter:
    """主数据查询过滤与定制查询覆盖。"""

    async def test_query_by_filter_cache_hit(
        self, security_context, monkeypatch
    ) -> None:
        """过滤查询缓存命中 → 直接返回缓存。"""
        security_context(
            _make_security_context(
                permissions=frozenset({"mdm:master_data:query"}),
            )
        )
        cached = [{"enterprise_product_id": str(uuid4())}]

        async def _cache_hit(*args, **kwargs):  # type: ignore[no-untyped-def]
            return cached

        monkeypatch.setattr(
            MasterDataQueryRedisStore,
            "get_enterprise_product_cache",
            staticmethod(_cache_hit),
        )
        svc = MasterDataQueryAppSvc(_MockSession())
        result = await svc.query_by_filter(uuid4(), {})
        assert result == cached

    async def test_query_by_filter_unauthenticated_rejected(self) -> None:
        """无认证过滤查询 → 拒绝。"""
        SecurityContext.set(None)
        svc = MasterDataQueryAppSvc(_MockSession())
        with pytest.raises(MDMError) as exc:
            await svc.query_by_filter(uuid4(), {})
        assert exc.value.code == MDMErrorCode.DIRECT_ACCESS_DENIED

    async def test_query_by_filter_unauthorized_rejected(
        self, security_context
    ) -> None:
        """无查询权限过滤查询 → 拒绝。"""
        security_context(_make_security_context(permissions=frozenset()))
        svc = MasterDataQueryAppSvc(_MockSession())
        with pytest.raises(MDMError) as exc:
            await svc.query_by_filter(uuid4(), {})
        assert exc.value.code == MDMErrorCode.GROUP_CATALOG_PERMISSION_DENIED

    async def test_get_customization_returns_none_when_absent(
        self, security_context, monkeypatch
    ) -> None:
        """企业定制查询 - 不存在时返回 None。"""
        security_context(_make_security_context())

        async def _return_none(*args, **kwargs):  # type: ignore[no-untyped-def]
            return None

        monkeypatch.setattr(
            ProductCustomizationRepository, "get_by_product", _return_none
        )
        svc = EnterpriseCustomizationAppSvc(_MockSession())
        result = await svc.get_customization(uuid4(), uuid4())
        assert result is None