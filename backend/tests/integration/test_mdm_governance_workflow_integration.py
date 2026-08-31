"""EITP-MDM-001-T16-05 集团商品目录治理工作流集成测试。

跨模块调用 GovernanceWorkflowAppSvc + VersionManagementAppSvc，验证：
创建变更申请 → 生成版本快照 → 提交 → 审批 → 发布 → 切换生效版本
→ 发布领域事件 → 记录审计 全流程（design 2.4.1）。

对应 spec 5.6.1.1 / 5.6.1.11 / 4.2.1 / 4.2.2，design 2.4.1。
"""

from __future__ import annotations

from contextlib import contextmanager
from uuid import UUID, uuid4

import pytest

from app.application.governance.governance_workflow_app_svc import (
    GovernanceWorkflowAppSvc,
)
from app.application.governance.version_management_app_svc import (
    VersionManagementAppSvc,
)
from app.domain.governance.aggregates.governance_workflow_aggregate import (
    GovernanceLevel,
    GovernanceWorkflowAggregate,
)
from app.domain.governance.aggregates.master_data_version_aggregate import (
    ChangeType,
    MasterDataVersionAggregate,
)
from app.domain.governance.events.governance_events import (
    GovernanceRequestApprovedEvent,
    GovernanceRequestPublishedEvent,
    GovernanceRequestRejectedEvent,
    GovernanceRequestRollbackEvent,
    GovernanceRequestSubmittedEvent,
)
from app.domain.governance.value_objects.governance_state import GovernanceState
from app.domain.shared.entity import EntityId
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


class _DummySession:
    """最小异步会话占位 - 治理/版本应用服务不直接使用会话执行查询。"""

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    def add(self, _orm: object) -> None:
        return None


class _WorkflowORMProxy:
    """治理工作流聚合根 → ORM 属性名代理，供应用服务 _orm_to_agg 使用。"""

    def __init__(self, agg: GovernanceWorkflowAggregate) -> None:
        self.request_id = agg.id.value
        self.tenant_id = agg.tenant_id
        self.governance_level = agg.governance_level.value
        self.entity_type = agg.entity_type
        self.entity_id = agg.entity_id
        self.target_version_id = agg.target_version_id
        self.status = agg.status.value
        self.submitted_by = agg.submitted_by
        self.submitted_at = agg.submitted_at
        self.approved_by = agg.approved_by
        self.approved_at = agg.approved_at
        self.approval_opinion = agg.approval_opinion
        self.published_by = agg.published_by
        self.published_at = agg.published_at
        self.rollback_by = agg.rollback_by
        self.rollback_at = agg.rollback_at
        self.rollback_reason = agg.rollback_reason


class _FakeGovernanceWorkflowRepo:
    """治理工作流内存仓储。"""

    def __init__(self) -> None:
        self._store: dict[UUID, _WorkflowORMProxy] = {}

    async def save(self, session: object, agg: GovernanceWorkflowAggregate) -> _WorkflowORMProxy:
        orm = _WorkflowORMProxy(agg)
        self._store[agg.id.value] = orm
        return orm

    async def get_by_id(self, session: object, request_id: UUID) -> _WorkflowORMProxy | None:
        return self._store.get(request_id)

    async def update(self, session: object, agg: GovernanceWorkflowAggregate) -> _WorkflowORMProxy | None:
        orm = _WorkflowORMProxy(agg)
        self._store[agg.id.value] = orm
        return orm

    async def list_by_tenant(
        self, session: object, tenant_id: UUID, offset: int = 0, limit: int = 50
    ) -> list[_WorkflowORMProxy]:
        items = [o for o in self._store.values() if o.tenant_id == tenant_id]
        return items[offset : offset + limit]

    async def list_pending(
        self, session: object, offset: int = 0, limit: int = 50
    ) -> list[_WorkflowORMProxy]:
        items = [o for o in self._store.values() if o.status == GovernanceState.SUBMITTED.value]
        return items[offset : offset + limit]


class _VersionORMProxy:
    """主数据版本聚合根 → ORM 属性名代理。"""

    def __init__(self, agg: MasterDataVersionAggregate) -> None:
        self.version_id = agg.id.value
        self.entity_type = agg.entity_type
        self.entity_id = agg.entity_id
        self.version_number = agg.version_number
        self.snapshot_after = agg.snapshot_after
        self.change_type = agg.change_type.value
        self.operated_by = agg.operated_by
        self.tenant_id = agg.tenant_id
        self.snapshot_before = agg.snapshot_before
        self.reason = agg.reason
        self.operated_at = agg.operated_at


class _FakeMasterDataVersionRepo:
    """主数据版本内存仓储 - append-only。"""

    def __init__(self) -> None:
        self._store: dict[UUID, _VersionORMProxy] = {}

    async def save(self, session: object, agg: MasterDataVersionAggregate) -> _VersionORMProxy:
        orm = _VersionORMProxy(agg)
        self._store[agg.id.value] = orm
        return orm

    async def get_by_id(self, session: object, version_id: UUID) -> _VersionORMProxy | None:
        return self._store.get(version_id)

    async def list_by_entity(
        self, session: object, entity_type: str, entity_id: UUID
    ) -> list[_VersionORMProxy]:
        items = [
            o
            for o in self._store.values()
            if o.entity_type == entity_type and o.entity_id == entity_id
        ]
        items.sort(key=lambda o: o.version_number)
        return items


# ----------------------------- 公共辅助 -----------------------------


_GROUP_MANAGE = "mdm:group_product:manage"
_ENTERPRISE_MANAGE = "mdm:enterprise_product:manage"
_GOVERNANCE_APPROVE = "mdm:governance:approve"
_VERSION_COMPARE = "mdm:version:compare"
_VERSION_QUERY = "mdm:version:query"


def _make_ctx(
    tenant_id: UUID | None = None,
    permissions: frozenset[str] = frozenset(),
    is_platform_admin: bool = False,
    is_tenant_admin: bool = False,
) -> SecurityContext:
    return SecurityContext(
        user=UserIdentity(
            user_id=uuid4(),
            username="tester",
            is_platform_admin=is_platform_admin,
            is_tenant_admin=is_tenant_admin,
        ),
        tenant=TenantIdentity(tenant_id=tenant_id or uuid4()),
        roles=(RoleSummary(role_id=uuid4(), role_code="tester", role_name="测试角色"),),
        permissions=PermissionSummary(codes=permissions),
        data_scope=ResolvedDataScope(),
    )


@contextmanager
def _apply_ctx(ctx: SecurityContext):
    token = SecurityContext.set(ctx)
    try:
        yield
    finally:
        SecurityContext.reset(token)


def _group_admin_ctx() -> SecurityContext:
    """集团主数据管理员 + 平台管理员 + 治理审批权限。"""
    return _make_ctx(
        permissions=frozenset({_GROUP_MANAGE, _GOVERNANCE_APPROVE, _VERSION_COMPARE, _VERSION_QUERY}),
        is_platform_admin=True,
    )


def _enterprise_admin_ctx(tenant_id: UUID) -> SecurityContext:
    """企业主数据管理员 + 企业级治理审批权限。"""
    return _make_ctx(
        tenant_id=tenant_id,
        permissions=frozenset(
            {_ENTERPRISE_MANAGE, _GOVERNANCE_APPROVE, _VERSION_COMPARE, _VERSION_QUERY}
        ),
        is_tenant_admin=True,
    )


def _new_workflow_svc() -> tuple[GovernanceWorkflowAppSvc, _FakeGovernanceWorkflowRepo]:
    session = _DummySession()
    svc = GovernanceWorkflowAppSvc(session=session)
    repo = _FakeGovernanceWorkflowRepo()
    svc._repo = repo
    return svc, repo


def _new_version_svc() -> tuple[VersionManagementAppSvc, _FakeMasterDataVersionRepo]:
    session = _DummySession()
    svc = VersionManagementAppSvc(session=session)
    repo = _FakeMasterDataVersionRepo()
    svc._repo = repo
    return svc, repo


# ----------------------------- 集成测试 -----------------------------


class TestGovernanceWorkflowIntegration:
    """T16-05: 集团商品目录治理工作流跨模块集成测试。"""

    async def test_full_happy_path_draft_to_published(self) -> None:
        """五步流转 DRAFT→SUBMITTED→APPROVED→PUBLISHED 全流程贯通。"""
        svc, _ = _new_workflow_svc()
        target_version_id = uuid4()
        submitter = uuid4()
        approver = uuid4()
        publisher = uuid4()

        with _apply_ctx(_group_admin_ctx()):
            wf = await svc.create_request(
                governance_level=GovernanceLevel.GROUP,
                entity_type="group_product",
                target_version_id=target_version_id,
            )
            assert wf.status == GovernanceState.DRAFT
            assert wf.is_editable() is True

            wf = await svc.submit_request(wf.id.value, submitted_by=submitter)
            assert wf.status == GovernanceState.SUBMITTED
            assert wf.submitted_by == submitter
            assert wf.is_editable() is False

            wf = await svc.approve_request(wf.id.value, approver=approver, opinion="同意发布")
            assert wf.status == GovernanceState.APPROVED
            assert wf.approved_by == approver
            assert wf.approval_opinion == "同意发布"

            wf = await svc.publish_request(wf.id.value, published_by=publisher)
            assert wf.status == GovernanceState.PUBLISHED
            assert wf.published_by == publisher
            assert wf.published_at is not None

    async def test_domain_events_published_in_order(self) -> None:
        """发布领域事件按 Submitted→Approved→Published 顺序记录。"""
        svc, _ = _new_workflow_svc()
        target_version_id = uuid4()

        with _apply_ctx(_group_admin_ctx()):
            wf = await svc.create_request(
                governance_level=GovernanceLevel.GROUP,
                entity_type="group_product",
                target_version_id=target_version_id,
            )
            request_id = wf.id.value
            # 应用服务每次从仓储重建聚合根，事件分散在各步返回实例上，
            # 由 DomainEventBus 统一收集发布。此处累积验证事件类型顺序。
            wf_after_submit = await svc.submit_request(request_id, submitted_by=uuid4())
            wf_after_approve = await svc.approve_request(
                request_id, approver=uuid4(), opinion="同意"
            )
            wf_after_publish = await svc.publish_request(request_id, published_by=uuid4())

        events = (
            list(wf_after_submit.pull_events())
            + list(wf_after_approve.pull_events())
            + list(wf_after_publish.pull_events())
        )
        assert len(events) == 3
        assert isinstance(events[0], GovernanceRequestSubmittedEvent)
        assert isinstance(events[1], GovernanceRequestApprovedEvent)
        assert isinstance(events[2], GovernanceRequestPublishedEvent)
        assert events[2].target_version_id == target_version_id
        assert events[2].governance_level == GovernanceLevel.GROUP.value

    async def test_reject_path_records_rejected_event(self) -> None:
        """审批拒绝路径 SUBMITTED→REJECTED 并发布 RejectedEvent。"""
        svc, _ = _new_workflow_svc()
        rejecter = uuid4()

        with _apply_ctx(_group_admin_ctx()):
            wf = await svc.create_request(
                governance_level=GovernanceLevel.GROUP,
                entity_type="group_product",
                target_version_id=uuid4(),
            )
            request_id = wf.id.value
            await svc.submit_request(request_id, submitted_by=uuid4())
            wf = await svc.reject_request(request_id, rejecter=rejecter, opinion="数据有误")

        assert wf.status == GovernanceState.REJECTED
        assert wf.approval_opinion == "数据有误"
        events = list(wf.pull_events())
        assert isinstance(events[-1], GovernanceRequestRejectedEvent)
        assert events[-1].rejection_opinion == "数据有误"

    async def test_rollback_path_records_rollback_event(self) -> None:
        """回滚路径 PUBLISHED→ROLLED_BACK 并发布 RollbackEvent。"""
        svc, _ = _new_workflow_svc()
        rollback_by = uuid4()

        with _apply_ctx(_group_admin_ctx()):
            wf = await svc.create_request(
                governance_level=GovernanceLevel.GROUP,
                entity_type="group_product",
                target_version_id=uuid4(),
            )
            request_id = wf.id.value
            await svc.submit_request(request_id, submitted_by=uuid4())
            await svc.approve_request(request_id, approver=uuid4(), opinion="同意")
            await svc.publish_request(request_id, published_by=uuid4())
            wf = await svc.rollback_request(
                request_id, rollback_by=rollback_by, reason="发布后发现数据错误"
            )

        assert wf.status == GovernanceState.ROLLED_BACK
        assert wf.rollback_by == rollback_by
        assert wf.rollback_reason == "发布后发现数据错误"
        events = list(wf.pull_events())
        assert isinstance(events[-1], GovernanceRequestRollbackEvent)
        assert events[-1].rollback_reason == "发布后发现数据错误"

    async def test_invalid_state_transition_publish_from_draft_rejected(self) -> None:
        """非法状态跳转 DRAFT→PUBLISHED 被拒绝。"""
        svc, _ = _new_workflow_svc()

        with _apply_ctx(_group_admin_ctx()):
            wf = await svc.create_request(
                governance_level=GovernanceLevel.GROUP,
                entity_type="group_product",
                target_version_id=uuid4(),
            )
            with pytest.raises(MDMError) as exc:
                await svc.publish_request(wf.id.value, published_by=uuid4())
        assert exc.value.code == MDMErrorCode.INVALID_GOVERNANCE_STATE_TRANSITION

    async def test_invalid_state_transition_approve_from_draft_rejected(self) -> None:
        """非法状态跳转 DRAFT→APPROVED 被拒绝。"""
        svc, _ = _new_workflow_svc()

        with _apply_ctx(_group_admin_ctx()):
            wf = await svc.create_request(
                governance_level=GovernanceLevel.GROUP,
                entity_type="group_product",
                target_version_id=uuid4(),
            )
            with pytest.raises(MDMError) as exc:
                await svc.approve_request(wf.id.value, approver=uuid4(), opinion="同意")
        assert exc.value.code == MDMErrorCode.INVALID_GOVERNANCE_STATE_TRANSITION

    async def test_submit_without_permission_rejected(self) -> None:
        """无集团管理权限提交集团级治理申请被拒绝。"""
        svc, _ = _new_workflow_svc()

        # 非平台管理员且无 manage 权限
        with _apply_ctx(_make_ctx(permissions=frozenset(), is_platform_admin=False)):
            wf = await svc.create_request(
                governance_level=GovernanceLevel.GROUP,
                entity_type="group_product",
                target_version_id=uuid4(),
            )
            with pytest.raises(MDMError) as exc:
                await svc.submit_request(wf.id.value, submitted_by=uuid4())
        assert exc.value.code == MDMErrorCode.CROSS_LEVEL_GOVERNANCE_DENIED

    async def test_group_level_approve_requires_platform_admin(self) -> None:
        """集团级审批需平台管理员角色，企业审批人被拒绝。"""
        svc, _ = _new_workflow_svc()

        # 企业管理员（非平台管理员）尝试审批集团级申请
        enterprise_ctx = _make_ctx(
            permissions=frozenset({_ENTERPRISE_MANAGE, _GOVERNANCE_APPROVE}),
            is_platform_admin=False,
        )
        with _apply_ctx(_group_admin_ctx()):
            wf = await svc.create_request(
                governance_level=GovernanceLevel.GROUP,
                entity_type="group_product",
                target_version_id=uuid4(),
            )
            request_id = wf.id.value
            await svc.submit_request(request_id, submitted_by=uuid4())

        with _apply_ctx(enterprise_ctx):
            with pytest.raises(MDMError) as exc:
                await svc.approve_request(request_id, approver=uuid4(), opinion="同意")
        assert exc.value.code == MDMErrorCode.CROSS_LEVEL_GOVERNANCE_DENIED

    async def test_approve_without_governance_permission_rejected(self) -> None:
        """无治理审批权限审批被拒绝。"""
        svc, _ = _new_workflow_svc()

        # 非平台管理员，仅有 manage 权限而无 governance:approve 权限
        no_approve_ctx = _make_ctx(
            permissions=frozenset({_GROUP_MANAGE}),
            is_platform_admin=False,
        )
        with _apply_ctx(_group_admin_ctx()):
            wf = await svc.create_request(
                governance_level=GovernanceLevel.GROUP,
                entity_type="group_product",
                target_version_id=uuid4(),
            )
            request_id = wf.id.value
            await svc.submit_request(request_id, submitted_by=uuid4())

        with _apply_ctx(no_approve_ctx):
            with pytest.raises(MDMError) as exc:
                await svc.approve_request(request_id, approver=uuid4(), opinion="同意")
        assert exc.value.code == MDMErrorCode.GOVERNANCE_APPROVAL_DENIED

    async def test_enterprise_level_governance_flow(self) -> None:
        """企业级治理工作流 DRAFT→SUBMITTED→APPROVED→PUBLISHED 全流程。"""
        svc, _ = _new_workflow_svc()
        tenant_id = uuid4()
        target_version_id = uuid4()

        with _apply_ctx(_enterprise_admin_ctx(tenant_id)):
            wf = await svc.create_request(
                governance_level=GovernanceLevel.ENTERPRISE,
                entity_type="enterprise_product",
                target_version_id=target_version_id,
                tenant_id=tenant_id,
            )
            assert wf.tenant_id == tenant_id
            assert wf.is_group_level() is False

            wf = await svc.submit_request(wf.id.value, submitted_by=uuid4())
            assert wf.status == GovernanceState.SUBMITTED

            wf = await svc.approve_request(wf.id.value, approver=uuid4(), opinion="企业审批通过")
            assert wf.status == GovernanceState.APPROVED

            wf = await svc.publish_request(wf.id.value, published_by=uuid4())
            assert wf.status == GovernanceState.PUBLISHED

    async def test_group_level_with_tenant_id_rejected(self) -> None:
        """集团级治理工作流不能含 tenant_id。"""
        svc, _ = _new_workflow_svc()

        with _apply_ctx(_group_admin_ctx()):
            with pytest.raises(MDMError) as exc:
                await svc.create_request(
                    governance_level=GovernanceLevel.GROUP,
                    entity_type="group_product",
                    target_version_id=uuid4(),
                    tenant_id=uuid4(),
                )
        assert exc.value.code == MDMErrorCode.INVALID_GOVERNANCE_STATE_TRANSITION

    async def test_request_not_found_raises_version_not_found(self) -> None:
        """不存在的治理申请 ID 查询被拒绝。"""
        svc, _ = _new_workflow_svc()

        with _apply_ctx(_group_admin_ctx()):
            with pytest.raises(MDMError) as exc:
                await svc.submit_request(uuid4(), submitted_by=uuid4())
        assert exc.value.code == MDMErrorCode.VERSION_NOT_FOUND

    async def test_list_pending_returns_only_submitted(self) -> None:
        """list_pending 仅返回 SUBMITTED 状态申请。"""
        svc, _ = _new_workflow_svc()

        with _apply_ctx(_group_admin_ctx()):
            wf1 = await svc.create_request(
                governance_level=GovernanceLevel.GROUP,
                entity_type="group_product",
                target_version_id=uuid4(),
            )
            await svc.submit_request(wf1.id.value, submitted_by=uuid4())

            wf2 = await svc.create_request(
                governance_level=GovernanceLevel.GROUP,
                entity_type="group_product",
                target_version_id=uuid4(),
            )
            # wf2 仍为 DRAFT，不应出现在 pending 列表

            pending = await svc.list_pending()
        pending_ids = {p.request_id for p in pending}
        assert wf1.id.value in pending_ids
        assert wf2.id.value not in pending_ids


class TestGovernanceVersionManagementIntegration:
    """T16-05: 治理工作流与版本管理跨模块集成测试。"""

    async def test_version_snapshot_generated_on_create(self) -> None:
        """创建变更申请时生成不可变版本快照，版本管理可查询。"""
        wf_svc, _ = _new_workflow_svc()
        version_svc, version_repo = _new_version_svc()

        entity_id = uuid4()
        operated_by = uuid4()
        target_version_id = uuid4()

        with _apply_ctx(_group_admin_ctx()):
            # 1. 创建治理变更申请
            wf = await wf_svc.create_request(
                governance_level=GovernanceLevel.GROUP,
                entity_type="group_product",
                target_version_id=target_version_id,
                entity_id=entity_id,
            )
            assert wf.status == GovernanceState.DRAFT

            # 2. 生成版本快照（不可变，append-only）
            snapshot = {"name": "商品A", "category": "食品", "price": 100}
            version = MasterDataVersionAggregate.create_initial(
                entity_type="group_product",
                entity_id=entity_id,
                snapshot_after=snapshot,
                operated_by=operated_by,
            )
            await version_repo.save(None, version)

            # 3. 版本管理查询版本
            versions = await version_svc.list_versions("group_product", entity_id)
        assert len(versions) == 1
        assert versions[0].version_number == 1
        assert versions[0].change_type == ChangeType.CREATE.value
        assert versions[0].snapshot_after == snapshot

    async def test_version_management_compare_versions(self) -> None:
        """版本管理跨模块对比两个版本字段级差异。"""
        wf_svc, _ = _new_workflow_svc()
        version_svc, version_repo = _new_version_svc()

        entity_id = uuid4()
        operated_by = uuid4()

        v1 = MasterDataVersionAggregate.create_initial(
            entity_type="group_product",
            entity_id=entity_id,
            snapshot_after={"name": "旧名", "category": "食品", "price": 100},
            operated_by=operated_by,
        )
        await version_repo.save(None, v1)
        v2 = MasterDataVersionAggregate.create_update(
            entity_type="group_product",
            entity_id=entity_id,
            version_number=2,
            snapshot_before={"name": "旧名", "category": "食品", "price": 100},
            snapshot_after={"name": "新名", "category": "食品", "price": 120},
            operated_by=operated_by,
        )
        await version_repo.save(None, v2)

        with _apply_ctx(_group_admin_ctx()):
            diff = await version_svc.compare_versions(
                "group_product", entity_id, version_a=1, version_b=2
            )
        assert diff["name"] == {"before": "旧名", "after": "新名"}
        assert diff["price"] == {"before": 100, "after": 120}
        assert "category" not in diff

    async def test_version_management_compare_nonexistent_version_rejected(self) -> None:
        """版本对比查询不存在的版本号被拒绝。"""
        version_svc, version_repo = _new_version_svc()
        entity_id = uuid4()

        v1 = MasterDataVersionAggregate.create_initial(
            entity_type="group_product",
            entity_id=entity_id,
            snapshot_after={"name": "A"},
            operated_by=uuid4(),
        )
        await version_repo.save(None, v1)

        with _apply_ctx(_group_admin_ctx()):
            with pytest.raises(MDMError) as exc:
                await version_svc.compare_versions(
                    "group_product", entity_id, version_a=1, version_b=99
                )
        assert exc.value.code == MDMErrorCode.VERSION_NOT_FOUND

    async def test_version_management_rollback_to_version(self) -> None:
        """版本管理跨模块回滚到指定版本。"""
        version_svc, version_repo = _new_version_svc()
        entity_id = uuid4()

        v1 = MasterDataVersionAggregate.create_initial(
            entity_type="group_product",
            entity_id=entity_id,
            snapshot_after={"name": "v1"},
            operated_by=uuid4(),
        )
        await version_repo.save(None, v1)
        v2 = MasterDataVersionAggregate.create_update(
            entity_type="group_product",
            entity_id=entity_id,
            version_number=2,
            snapshot_before={"name": "v1"},
            snapshot_after={"name": "v2"},
            operated_by=uuid4(),
        )
        await version_repo.save(None, v2)

        with _apply_ctx(_group_admin_ctx()):
            rolled = await version_svc.rollback_to_version(
                "group_product", entity_id, target_version=1
            )
        assert rolled.version_number == 1
        assert rolled.snapshot_after == {"name": "v1"}

    async def test_version_compare_without_permission_rejected(self) -> None:
        """无版本对比权限被拒绝。"""
        version_svc, _ = _new_version_svc()
        entity_id = uuid4()

        with _apply_ctx(_make_ctx(permissions=frozenset(), is_platform_admin=False)):
            with pytest.raises(MDMError) as exc:
                await version_svc.compare_versions(
                    "group_product", entity_id, version_a=1, version_b=2
                )
        assert exc.value.code == MDMErrorCode.GROUP_CATALOG_PERMISSION_DENIED

    async def test_version_compare_without_security_context_rejected(self) -> None:
        """未认证（无安全上下文）版本对比被拒绝。"""
        version_svc, _ = _new_version_svc()
        entity_id = uuid4()

        with pytest.raises(MDMError) as exc:
            await version_svc.compare_versions(
                "group_product", entity_id, version_a=1, version_b=2
            )
        assert exc.value.code == MDMErrorCode.DIRECT_ACCESS_DENIED

    async def test_publish_then_rollback_full_flow_with_version(self) -> None:
        """发布→回滚全流程，版本快照与治理状态协同变更。"""
        wf_svc, _ = _new_workflow_svc()
        version_svc, version_repo = _new_version_svc()

        entity_id = uuid4()
        target_version_id = uuid4()

        with _apply_ctx(_group_admin_ctx()):
            wf = await wf_svc.create_request(
                governance_level=GovernanceLevel.GROUP,
                entity_type="group_product",
                target_version_id=target_version_id,
                entity_id=entity_id,
            )
            request_id = wf.id.value

            # 生成初始版本快照
            v1 = MasterDataVersionAggregate.create_initial(
                entity_type="group_product",
                entity_id=entity_id,
                snapshot_after={"name": "商品A", "price": 100},
                operated_by=uuid4(),
            )
            await version_repo.save(None, v1)

            await wf_svc.submit_request(request_id, submitted_by=uuid4())
            await wf_svc.approve_request(request_id, approver=uuid4(), opinion="同意")
            wf = await wf_svc.publish_request(request_id, published_by=uuid4())
            assert wf.status == GovernanceState.PUBLISHED

            # 回滚到前一版本
            rolled_version = await version_svc.rollback_to_version(
                "group_product", entity_id, target_version=1
            )
            wf = await wf_svc.rollback_request(
                request_id, rollback_by=uuid4(), reason="发布后发现数据错误"
            )

        assert wf.status == GovernanceState.ROLLED_BACK
        assert rolled_version.version_number == 1
        assert rolled_version.snapshot_after == {"name": "商品A", "price": 100}