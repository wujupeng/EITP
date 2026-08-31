"""EITP-MDM-001-T16-08 负库存策略审计集成测试。

跨模块调用 NegativePolicyAppSvc + NegativeInventoryPolicyAuditWriter，验证：
默认 STRICT 强制 → 策略变更原因必填 → 策略更新与审计写入原子完成
→ 策略变更历史检索按租户隔离（design 2.7）。

对应 spec 5.9.1.1 / 5.9.1.3 / 5.9.1.4 / 5.9.1.5 / 5.9.1.7 / 5.9.1.8 / 5.9.1.9，design 2.7。
"""

from __future__ import annotations

from contextlib import contextmanager
from uuid import UUID, uuid4

import pytest

from app.application.governance.negative_inventory_policy_audit_writer import (
    NegativeInventoryPolicyAuditWriter,
)
from app.application.governance.negative_policy_app_svc import NegativePolicyAppSvc
from app.domain.governance.aggregates.negative_inventory_policy_audit_aggregate import (
    NegativeInventoryPolicyAuditAggregate,
    NegativePolicyMode,
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


# ----------------------------- 测试替身 -----------------------------


class _PolicySession:
    """负库存策略内存会话 - 维护策略表与待提交缓冲。"""

    def __init__(self) -> None:
        self.policies: dict[UUID, object] = {}
        self._pending: object | None = None

    def add(self, orm: object) -> None:
        self._pending = orm

    async def flush(self) -> None:
        if self._pending is not None:
            self.policies[getattr(self._pending, "tenant_id")] = self._pending
            self._pending = None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        self._pending = None


class _FakeAuditRepo:
    """负库存策略审计内存仓储 - append-only。"""

    def __init__(self) -> None:
        self.records: list[NegativeInventoryPolicyAuditAggregate] = []

    async def save(self, session: object, agg: NegativeInventoryPolicyAuditAggregate) -> None:
        self.records.append(agg)

    async def list_by_tenant(
        self, session: object, tenant_id: UUID, offset: int = 0, limit: int = 50
    ) -> list[NegativeInventoryPolicyAuditAggregate]:
        items = [r for r in self.records if r.tenant_id == tenant_id]
        return items[offset : offset + limit]


# ----------------------------- 公共辅助 -----------------------------


_POLICY_CONFIG = "mdm:negative_policy:config"
_POLICY_AUDIT_QUERY = "mdm:negative_policy:audit:query"


def _make_ctx(
    tenant_id: UUID,
    permissions: frozenset[str] = frozenset({_POLICY_CONFIG, _POLICY_AUDIT_QUERY}),
    is_platform_admin: bool = False,
    is_tenant_admin: bool = True,
) -> SecurityContext:
    return SecurityContext(
        user=UserIdentity(
            user_id=uuid4(),
            username="tenant-admin",
            is_platform_admin=is_platform_admin,
            is_tenant_admin=is_tenant_admin,
        ),
        tenant=TenantIdentity(tenant_id=tenant_id),
        roles=(RoleSummary(role_id=uuid4(), role_code="tenant_admin", role_name="租户管理员"),),
        permissions=PermissionSummary(codes=permissions),
        data_scope=ResolvedDataScope(scope_type="tenant"),
    )


@contextmanager
def _apply_ctx(ctx: SecurityContext):
    token = SecurityContext.set(ctx)
    try:
        yield
    finally:
        SecurityContext.reset(token)


def _new_policy_svc() -> tuple[
    NegativePolicyAppSvc,
    _PolicySession,
    _FakeAuditRepo,
    dict[UUID, object],
]:
    """构造 NegativePolicyAppSvc，_load_policy 从内存策略表读取。"""
    session = _PolicySession()
    svc = NegativePolicyAppSvc(session=session)
    audit_repo = _FakeAuditRepo()
    svc._audit_repo = audit_repo

    policies = session.policies

    async def fake_load_policy(tenant_id: UUID):
        return policies.get(tenant_id)

    # 替换实例方法为内存读取（避开 SQLAlchemy select 解析）
    svc._load_policy = fake_load_policy  # type: ignore[method-assign]
    return svc, session, audit_repo, policies


# ----------------------------- 集成测试 -----------------------------


class TestNegativePolicyDefaultStrictIntegration:
    """T16-08: 默认 STRICT 强制集成测试（design 2.7.1）。"""

    async def test_default_policy_is_strict_when_no_record(self) -> None:
        """无策略记录时默认返回 STRICT（spec 5.9.1.1）。"""
        svc, _, _, _ = _new_policy_svc()
        tenant_id = uuid4()

        with _apply_ctx(_make_ctx(tenant_id)):
            policy = await svc.get_current_policy(tenant_id)

        assert policy == NegativePolicyMode.STRICT

    async def test_initialize_default_policy_strict(self) -> None:
        """新租户初始化默认 STRICT 策略（spec 5.9.1.1/5.9.1.8）。"""
        svc, session, _, policies = _new_policy_svc()
        tenant_id = uuid4()

        await svc.initialize_default_policy(tenant_id)

        assert tenant_id in policies
        assert policies[tenant_id].mode == "global_forbid"

    async def test_initialize_default_policy_idempotent(self) -> None:
        """已存在策略时初始化不覆盖。"""
        svc, _, _, policies = _new_policy_svc()
        tenant_id = uuid4()

        # 预置一个非默认策略
        from app.infrastructure.inventory.models import NegativeStockPolicyORM

        existing = NegativeStockPolicyORM(tenant_id=tenant_id, mode="global_allow")
        policies[tenant_id] = existing

        await svc.initialize_default_policy(tenant_id)
        # 不覆盖已有策略
        assert policies[tenant_id].mode == "global_allow"

    def test_initialize_default_non_strict_rejected(self) -> None:
        """新租户默认策略非 STRICT 被拒绝（spec 5.9.1.8）。"""
        with pytest.raises(MDMError) as exc:
            NegativeInventoryPolicyAuditAggregate.validate_default_must_strict(
                NegativePolicyMode.ALLOW, is_new_tenant=True
            )
        assert exc.value.code == MDMErrorCode.NEGATIVE_POLICY_DEFAULT_MUST_STRICT

    def test_validate_default_strict_passes(self) -> None:
        """新租户默认 STRICT 校验通过。"""
        NegativeInventoryPolicyAuditAggregate.validate_default_must_strict(
            NegativePolicyMode.STRICT, is_new_tenant=True
        )


class TestNegativePolicyChangeIntegration:
    """T16-08: 策略变更与审计写入集成测试（design 2.7.2）。"""

    async def test_change_policy_strict_to_allow_writes_audit(self) -> None:
        """策略变更 STRICT→ALLOW 原子写入审计记录。"""
        svc, _, audit_repo, _ = _new_policy_svc()
        tenant_id = uuid4()

        with _apply_ctx(_make_ctx(tenant_id)):
            audit_agg = await svc.change_policy(
                tenant_id=tenant_id,
                new_policy=NegativePolicyMode.ALLOW,
                reason="业务需要允许负库存",
            )

        assert audit_agg.policy_before == NegativePolicyMode.STRICT
        assert audit_agg.policy_after == NegativePolicyMode.ALLOW
        assert audit_agg.reason == "业务需要允许负库存"
        assert audit_agg.tenant_id == tenant_id
        # 审计记录已写入
        assert len(audit_repo.records) == 1
        assert audit_repo.records[0].policy_after == NegativePolicyMode.ALLOW

    async def test_change_policy_updates_effective_policy(self) -> None:
        """策略变更后 get_current_policy 返回新策略。"""
        svc, _, _, _ = _new_policy_svc()
        tenant_id = uuid4()

        with _apply_ctx(_make_ctx(tenant_id)):
            await svc.change_policy(
                tenant_id=tenant_id,
                new_policy=NegativePolicyMode.WARNING,
                reason="改为警告模式",
            )
            current = await svc.get_current_policy(tenant_id)

        assert current == NegativePolicyMode.WARNING

    async def test_change_policy_reason_required(self) -> None:
        """策略变更原因必填（spec 5.9.1.5）。"""
        svc, _, _, _ = _new_policy_svc()
        tenant_id = uuid4()

        with _apply_ctx(_make_ctx(tenant_id)):
            with pytest.raises(MDMError) as exc:
                await svc.change_policy(
                    tenant_id=tenant_id,
                    new_policy=NegativePolicyMode.ALLOW,
                    reason="",
                )
        assert exc.value.code == MDMErrorCode.NEGATIVE_POLICY_REASON_REQUIRED

    async def test_change_policy_reason_whitespace_rejected(self) -> None:
        """策略变更原因仅空白被拒绝。"""
        svc, _, _, _ = _new_policy_svc()
        tenant_id = uuid4()

        with _apply_ctx(_make_ctx(tenant_id)):
            with pytest.raises(MDMError) as exc:
                await svc.change_policy(
                    tenant_id=tenant_id,
                    new_policy=NegativePolicyMode.ALLOW,
                    reason="   ",
                )
        assert exc.value.code == MDMErrorCode.NEGATIVE_POLICY_REASON_REQUIRED

    async def test_change_policy_no_change_rejected(self) -> None:
        """策略未变化时拒绝写入审计。"""
        svc, _, _, policies = _new_policy_svc()
        tenant_id = uuid4()

        from app.infrastructure.inventory.models import NegativeStockPolicyORM

        policies[tenant_id] = NegativeStockPolicyORM(tenant_id=tenant_id, mode="global_allow")

        with _apply_ctx(_make_ctx(tenant_id)):
            with pytest.raises(MDMError) as exc:
                await svc.change_policy(
                    tenant_id=tenant_id,
                    new_policy=NegativePolicyMode.ALLOW,
                    reason="无变化",
                )
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    async def test_change_policy_cross_tenant_rejected(self) -> None:
        """跨租户修改负库存策略被拒绝（spec 5.9.1.3）。"""
        svc, _, _, _ = _new_policy_svc()
        tenant_a = uuid4()
        tenant_b = uuid4()

        # 安全上下文为租户 A，尝试修改租户 B 的策略
        with _apply_ctx(_make_ctx(tenant_a)):
            with pytest.raises(MDMError) as exc:
                await svc.change_policy(
                    tenant_id=tenant_b,
                    new_policy=NegativePolicyMode.ALLOW,
                    reason="跨租户修改",
                )
        assert exc.value.code == MDMErrorCode.CROSS_TENANT_POLICY_DENIED

    async def test_change_policy_without_permission_rejected(self) -> None:
        """无策略配置权限修改被拒绝（spec 5.9.1.3）。"""
        svc, _, _, _ = _new_policy_svc()
        tenant_id = uuid4()

        # 有审计查询权限但无配置权限
        ctx = _make_ctx(tenant_id, permissions=frozenset({_POLICY_AUDIT_QUERY}))
        with _apply_ctx(ctx):
            with pytest.raises(MDMError) as exc:
                await svc.change_policy(
                    tenant_id=tenant_id,
                    new_policy=NegativePolicyMode.ALLOW,
                    reason="无权限修改",
                )
        assert exc.value.code == MDMErrorCode.NEGATIVE_POLICY_PERMISSION_DENIED

    async def test_change_policy_without_security_context_rejected(self) -> None:
        """未认证修改策略被拒绝。"""
        svc, _, _, _ = _new_policy_svc()
        tenant_id = uuid4()

        with pytest.raises(MDMError) as exc:
            await svc.change_policy(
                tenant_id=tenant_id,
                new_policy=NegativePolicyMode.ALLOW,
                reason="未认证",
            )
        assert exc.value.code == MDMErrorCode.DIRECT_ACCESS_DENIED

    async def test_multiple_changes_all_audited(self) -> None:
        """多次策略变更均写入审计，append-only。"""
        svc, _, audit_repo, _ = _new_policy_svc()
        tenant_id = uuid4()

        with _apply_ctx(_make_ctx(tenant_id)):
            await svc.change_policy(
                tenant_id=tenant_id,
                new_policy=NegativePolicyMode.ALLOW,
                reason="第一次变更",
            )
            await svc.change_policy(
                tenant_id=tenant_id,
                new_policy=NegativePolicyMode.WARNING,
                reason="第二次变更",
            )
            await svc.change_policy(
                tenant_id=tenant_id,
                new_policy=NegativePolicyMode.APPROVAL,
                reason="第三次变更",
            )

        assert len(audit_repo.records) == 3
        assert audit_repo.records[0].policy_before == NegativePolicyMode.STRICT
        assert audit_repo.records[0].policy_after == NegativePolicyMode.ALLOW
        assert audit_repo.records[1].policy_before == NegativePolicyMode.ALLOW
        assert audit_repo.records[1].policy_after == NegativePolicyMode.WARNING
        assert audit_repo.records[2].policy_before == NegativePolicyMode.WARNING
        assert audit_repo.records[2].policy_after == NegativePolicyMode.APPROVAL


class TestNegativePolicyAuditHistoryIntegration:
    """T16-08: 策略变更历史检索按租户隔离集成测试（design 2.7.4）。"""

    async def test_list_audit_history_tenant_isolated(self) -> None:
        """审计历史检索按租户隔离，仅返回本租户记录。"""
        svc, _, audit_repo, _ = _new_policy_svc()
        tenant_a = uuid4()
        tenant_b = uuid4()

        with _apply_ctx(_make_ctx(tenant_a)):
            await svc.change_policy(
                tenant_id=tenant_a,
                new_policy=NegativePolicyMode.ALLOW,
                reason="租户A变更",
            )
        with _apply_ctx(_make_ctx(tenant_b)):
            await svc.change_policy(
                tenant_id=tenant_b,
                new_policy=NegativePolicyMode.WARNING,
                reason="租户B变更",
            )

        # 租户 A 仅看到自己的审计记录
        with _apply_ctx(_make_ctx(tenant_a)):
            a_history = await svc.list_audit_history(tenant_a)
        assert len(a_history) == 1
        assert a_history[0].tenant_id == tenant_a
        assert a_history[0].reason == "租户A变更"

        # 租户 B 仅看到自己的审计记录
        with _apply_ctx(_make_ctx(tenant_b)):
            b_history = await svc.list_audit_history(tenant_b)
        assert len(b_history) == 1
        assert b_history[0].tenant_id == tenant_b

    async def test_list_audit_history_cross_tenant_rejected(self) -> None:
        """跨租户查询审计历史被拒绝。"""
        svc, _, _, _ = _new_policy_svc()
        tenant_a = uuid4()
        tenant_b = uuid4()

        with _apply_ctx(_make_ctx(tenant_a)):
            with pytest.raises(MDMError) as exc:
                await svc.list_audit_history(tenant_b)
        assert exc.value.code == MDMErrorCode.CROSS_TENANT_POLICY_DENIED

    async def test_list_audit_history_without_permission_rejected(self) -> None:
        """无审计查询权限查询被拒绝。"""
        svc, _, _, _ = _new_policy_svc()
        tenant_id = uuid4()

        ctx = _make_ctx(tenant_id, permissions=frozenset({_POLICY_CONFIG}))
        with _apply_ctx(ctx):
            with pytest.raises(MDMError) as exc:
                await svc.list_audit_history(tenant_id)
        assert exc.value.code == MDMErrorCode.NEGATIVE_POLICY_PERMISSION_DENIED

    async def test_list_audit_history_without_security_context_rejected(self) -> None:
        """未认证查询审计历史被拒绝。"""
        svc, _, _, _ = _new_policy_svc()
        with pytest.raises(MDMError) as exc:
            await svc.list_audit_history(uuid4())
        assert exc.value.code == MDMErrorCode.DIRECT_ACCESS_DENIED

    async def test_platform_admin_can_query_any_tenant_history(self) -> None:
        """平台管理员可查询任意租户审计历史。"""
        svc, _, _, _ = _new_policy_svc()
        tenant_a = uuid4()
        platform_admin_tenant = uuid4()

        with _apply_ctx(_make_ctx(tenant_a)):
            await svc.change_policy(
                tenant_id=tenant_a,
                new_policy=NegativePolicyMode.ALLOW,
                reason="租户A变更",
            )

        # 平台管理员查询租户 A 的审计历史
        admin_ctx = _make_ctx(
            platform_admin_tenant,
            permissions=frozenset({_POLICY_CONFIG, _POLICY_AUDIT_QUERY}),
            is_platform_admin=True,
        )
        with _apply_ctx(admin_ctx):
            history = await svc.list_audit_history(tenant_a)
        assert len(history) == 1
        assert history[0].tenant_id == tenant_a


class TestNegativePolicyGetCurrentIntegration:
    """T16-08: 策略查询集成测试。"""

    async def test_get_current_policy_cross_tenant_rejected(self) -> None:
        """跨租户查询当前策略被拒绝。"""
        svc, _, _, _ = _new_policy_svc()
        tenant_a = uuid4()
        tenant_b = uuid4()

        with _apply_ctx(_make_ctx(tenant_a)):
            with pytest.raises(MDMError) as exc:
                await svc.get_current_policy(tenant_b)
        assert exc.value.code == MDMErrorCode.CROSS_TENANT_POLICY_DENIED

    async def test_get_current_policy_without_security_context_rejected(self) -> None:
        """未认证查询当前策略被拒绝。"""
        svc, _, _, _ = _new_policy_svc()
        with pytest.raises(MDMError) as exc:
            await svc.get_current_policy(uuid4())
        assert exc.value.code == MDMErrorCode.DIRECT_ACCESS_DENIED

    async def test_platform_admin_can_query_any_tenant_policy(self) -> None:
        """平台管理员可查询任意租户当前策略。"""
        svc, _, _, _ = _new_policy_svc()
        tenant_a = uuid4()
        platform_admin_tenant = uuid4()

        admin_ctx = _make_ctx(
            platform_admin_tenant,
            permissions=frozenset({_POLICY_CONFIG, _POLICY_AUDIT_QUERY}),
            is_platform_admin=True,
        )
        with _apply_ctx(admin_ctx):
            policy = await svc.get_current_policy(tenant_a)
        assert policy == NegativePolicyMode.STRICT


class TestNegativeInventoryPolicyAuditWriterIntegration:
    """T16-08: 负库存策略审计写入器集成测试。"""

    async def test_writer_enforce_permission_tenant_match(self) -> None:
        """writer 权限校验：同租户 + 配置权限通过。"""
        tenant_id = uuid4()
        with _apply_ctx(_make_ctx(tenant_id)):
            NegativeInventoryPolicyAuditWriter.enforce_permission(tenant_id)

    def test_writer_enforce_permission_cross_tenant_rejected(self) -> None:
        """writer 权限校验：跨租户被拒绝。"""
        tenant_a = uuid4()
        tenant_b = uuid4()
        with _apply_ctx(_make_ctx(tenant_a)):
            with pytest.raises(MDMError) as exc:
                NegativeInventoryPolicyAuditWriter.enforce_permission(tenant_b)
        assert exc.value.code == MDMErrorCode.CROSS_TENANT_POLICY_DENIED

    def test_writer_enforce_permission_without_config_permission_rejected(self) -> None:
        """writer 权限校验：无配置权限被拒绝。"""
        tenant_id = uuid4()
        ctx = _make_ctx(tenant_id, permissions=frozenset({_POLICY_AUDIT_QUERY}))
        with _apply_ctx(ctx):
            with pytest.raises(MDMError) as exc:
                NegativeInventoryPolicyAuditWriter.enforce_permission(tenant_id)
        assert exc.value.code == MDMErrorCode.NEGATIVE_POLICY_PERMISSION_DENIED

    def test_writer_enforce_permission_without_security_context_rejected(self) -> None:
        """writer 权限校验：未认证被拒绝。"""
        with pytest.raises(MDMError) as exc:
            NegativeInventoryPolicyAuditWriter.enforce_permission(uuid4())
        assert exc.value.code == MDMErrorCode.NEGATIVE_POLICY_PERMISSION_DENIED

    def test_writer_write_audit_reason_required(self) -> None:
        """writer 写审计：原因必填。"""
        with pytest.raises(MDMError) as exc:
            NegativeInventoryPolicyAuditWriter.write_audit(
                tenant_id=uuid4(),
                policy_before=NegativePolicyMode.STRICT,
                policy_after=NegativePolicyMode.ALLOW,
                operated_by=uuid4(),
                reason="",
            )
        assert exc.value.code == MDMErrorCode.NEGATIVE_POLICY_REASON_REQUIRED

    def test_writer_write_audit_no_change_rejected(self) -> None:
        """writer 写审计：策略未变化被拒绝。"""
        with pytest.raises(MDMError) as exc:
            NegativeInventoryPolicyAuditWriter.write_audit(
                tenant_id=uuid4(),
                policy_before=NegativePolicyMode.ALLOW,
                policy_after=NegativePolicyMode.ALLOW,
                operated_by=uuid4(),
                reason="无变化",
            )
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_writer_change_policy_with_audit_atomic(self) -> None:
        """writer 策略变更并写入审计原子完成（权限校验+审计写入）。"""
        tenant_id = uuid4()
        operated_by = uuid4()
        with _apply_ctx(_make_ctx(tenant_id)):
            audit_agg = NegativeInventoryPolicyAuditWriter.change_policy_with_audit(
                tenant_id=tenant_id,
                policy_before=NegativePolicyMode.STRICT,
                policy_after=NegativePolicyMode.WARNING,
                operated_by=operated_by,
                reason="改为警告模式",
            )
        assert audit_agg.policy_before == NegativePolicyMode.STRICT
        assert audit_agg.policy_after == NegativePolicyMode.WARNING
        assert audit_agg.operated_by == operated_by
        assert audit_agg.reason == "改为警告模式"

    def test_writer_change_policy_with_audit_permission_denied(self) -> None:
        """writer 策略变更无权限被拒绝，审计不写入。"""
        tenant_id = uuid4()
        ctx = _make_ctx(tenant_id, permissions=frozenset({_POLICY_AUDIT_QUERY}))
        with _apply_ctx(ctx):
            with pytest.raises(MDMError) as exc:
                NegativeInventoryPolicyAuditWriter.change_policy_with_audit(
                    tenant_id=tenant_id,
                    policy_before=NegativePolicyMode.STRICT,
                    policy_after=NegativePolicyMode.ALLOW,
                    operated_by=uuid4(),
                    reason="无权限",
                )
        assert exc.value.code == MDMErrorCode.NEGATIVE_POLICY_PERMISSION_DENIED


class TestNegativePolicyAuditAggregateIntegration:
    """T16-08: 负库存策略审计聚合根集成测试。"""

    def test_audit_aggregate_create_reason_required(self) -> None:
        """审计聚合根创建原因必填。"""
        with pytest.raises(MDMError) as exc:
            NegativeInventoryPolicyAuditAggregate.create(
                tenant_id=uuid4(),
                policy_before=NegativePolicyMode.STRICT,
                policy_after=NegativePolicyMode.ALLOW,
                operated_by=uuid4(),
                reason="",
            )
        assert exc.value.code == MDMErrorCode.NEGATIVE_POLICY_REASON_REQUIRED

    def test_audit_aggregate_create_success(self) -> None:
        """审计聚合根创建成功，字段完整。"""
        tenant_id = uuid4()
        operated_by = uuid4()
        agg = NegativeInventoryPolicyAuditAggregate.create(
            tenant_id=tenant_id,
            policy_before=NegativePolicyMode.STRICT,
            policy_after=NegativePolicyMode.APPROVAL,
            operated_by=operated_by,
            reason="改为审批模式",
        )
        assert agg.audit_id is not None
        assert agg.tenant_id == tenant_id
        assert agg.policy_before == NegativePolicyMode.STRICT
        assert agg.policy_after == NegativePolicyMode.APPROVAL
        assert agg.operated_by == operated_by
        assert agg.reason == "改为审批模式"
        assert agg.operated_at is not None


class TestNegativePolicyFullFlowIntegration:
    """T16-08: 负库存策略审计全流程集成测试。"""

    async def test_full_flow_default_change_audit_query(self) -> None:
        """全流程：默认 STRICT → 变更策略 → 审计写入 → 历史检索按租户隔离。"""
        svc, _, audit_repo, _ = _new_policy_svc()
        tenant_a = uuid4()
        tenant_b = uuid4()

        # 1. 默认 STRICT 强制
        with _apply_ctx(_make_ctx(tenant_a)):
            initial_policy = await svc.get_current_policy(tenant_a)
        assert initial_policy == NegativePolicyMode.STRICT

        # 2. 租户 A 变更策略（原因必填，原子写入审计）
        with _apply_ctx(_make_ctx(tenant_a)):
            audit_a = await svc.change_policy(
                tenant_id=tenant_a,
                new_policy=NegativePolicyMode.WARNING,
                reason="租户A改为警告模式",
            )
        assert audit_a.policy_before == NegativePolicyMode.STRICT
        assert audit_a.policy_after == NegativePolicyMode.WARNING

        # 3. 租户 B 变更策略
        with _apply_ctx(_make_ctx(tenant_b)):
            audit_b = await svc.change_policy(
                tenant_id=tenant_b,
                new_policy=NegativePolicyMode.APPROVAL,
                reason="租户B改为审批模式",
            )
        assert audit_b.policy_after == NegativePolicyMode.APPROVAL

        # 4. 审计历史检索按租户隔离
        with _apply_ctx(_make_ctx(tenant_a)):
            a_history = await svc.list_audit_history(tenant_a)
        assert len(a_history) == 1
        assert a_history[0].tenant_id == tenant_a
        assert a_history[0].reason == "租户A改为警告模式"

        with _apply_ctx(_make_ctx(tenant_b)):
            b_history = await svc.list_audit_history(tenant_b)
        assert len(b_history) == 1
        assert b_history[0].tenant_id == tenant_b

        # 5. 审计记录 append-only，共 2 条
        assert len(audit_repo.records) == 2
        assert {r.tenant_id for r in audit_repo.records} == {tenant_a, tenant_b}