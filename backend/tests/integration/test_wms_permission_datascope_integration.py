"""EITP-WMS T16-10 权限验证与 DataScope 收敛集成测试。

跨模块调用 WmsTaskAppSvc/ReceivingAppSvc + SecurityContext/ResolvedDataScope，
验证：
- 权限模型：无 wms:receiving:execute 权限 is_authorized 返回 False（拒绝前提）
- 跨租户操作被拒绝（_check_auth 行级隔离）
- 越权领取他人 Task 被拒绝 + 越权不写审计
- DataScope 收敛：仅授权仓库 W1 的用户操作 W2 时 is_subset 返回 False
"""

from __future__ import annotations

from contextlib import contextmanager
from uuid import UUID, uuid4

import pytest

from app.application.warehouse.receiving_app_svc import ReceivingAppSvc
from app.application.warehouse.wms_task_app_svc import WmsTaskAppSvc
from app.infrastructure.warehouse.models import (
    WmsOperationAuditORM,
    WmsReceivingLineORM,
    WmsReceivingOrderORM,
    WmsTaskORM,
    WmsZoneORM,
)
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode
from app.interfaces.middleware.security_context import (
    AccessMode,
    PermissionSummary,
    ResolvedDataScope,
    RoleSummary,
    SecurityContext,
    TenantIdentity,
    UserIdentity,
)


# ----------------------------- 测试替身 -----------------------------


class _RecordingSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    def add(self, orm: object) -> None:
        self.added.append(orm)


def _ensure_id(orm: object, attr: str) -> None:
    if getattr(orm, attr) is None:
        setattr(orm, attr, uuid4())


class _FakeTaskRepo:
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID], WmsTaskORM] = {}

    async def get_by_id(self, session, tenant_id, task_id):
        return self._store.get((tenant_id, task_id))

    async def get_by_idempotency_key(self, session, tenant_id, key):
        return None

    async def save(self, session, orm):
        _ensure_id(orm, "task_id")
        self._store[(orm.tenant_id, orm.task_id)] = orm
        return orm

    async def update_status(self, session, tenant_id, task_id, new_status, **kwargs):
        orm = self._store.get((tenant_id, task_id))
        if orm is not None:
            orm.status = new_status
            if kwargs.get("assigned_at"):
                orm.assigned_at = kwargs["assigned_at"]
            if kwargs.get("started_at"):
                orm.started_at = kwargs["started_at"]

    async def list_by_status(self, session, tenant_id, status, offset=0, limit=50):
        return [orm for (t, _tid), orm in self._store.items() if t == tenant_id and orm.status == status]

    async def list_by_assignee(self, session, tenant_id, assignee_id, status=None):
        return [
            orm
            for (t, _tid), orm in self._store.items()
            if t == tenant_id
            and orm.assignee_id == assignee_id
            and (status is None or orm.status == status)
        ]


class _FakeReceivingRepo:
    def __init__(self) -> None:
        self._orders: dict[tuple[UUID, UUID], WmsReceivingOrderORM] = {}
        self._lines: dict[UUID, list[WmsReceivingLineORM]] = {}

    async def get_by_id(self, session, tenant_id, receiving_id):
        return self._orders.get((tenant_id, receiving_id))

    async def list_lines(self, session, tenant_id, receiving_id):
        return list(self._lines.get(receiving_id, []))

    async def update_line_received(self, session, line_orm, received_qty):
        line_orm.received_quantity = received_qty


class _FakeZoneRepo:
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID], WmsZoneORM] = {}

    async def get_by_id(self, session, tenant_id, zone_id):
        return self._store.get((tenant_id, zone_id))


class _FakePositionRepo:
    def __init__(self) -> None:
        self.upserted: list = []

    async def query_by_sku_location_status(self, session, tenant_id, sku_id, location_id, status):
        return None

    async def upsert(self, session, orm):
        self.upserted.append(orm)
        return orm


class _MockInvAppSvc:
    async def execute_transaction(self, **kwargs):
        return {"transaction_id": str(uuid4()), "status": "completed"}


# ----------------------------- 公共辅助 -----------------------------


def _make_ctx(
    tenant_id: UUID,
    permissions: frozenset[str] = frozenset(),
    is_platform_admin: bool = False,
    warehouse_ids: frozenset[UUID] = frozenset(),
    scope_type: str = "tenant",
) -> SecurityContext:
    return SecurityContext(
        user=UserIdentity(
            user_id=uuid4(), username="wms-user", is_platform_admin=is_platform_admin, is_tenant_admin=True
        ),
        tenant=TenantIdentity(tenant_id=tenant_id),
        roles=(RoleSummary(role_id=uuid4(), role_code="wms_worker", role_name="WMS作业员"),),
        permissions=PermissionSummary(codes=permissions),
        data_scope=ResolvedDataScope(
            scope_type=scope_type,
            warehouse_ids=warehouse_ids,
            access_mode=AccessMode.WRITE,
        ),
    )


@contextmanager
def _apply_ctx(ctx: SecurityContext):
    token = SecurityContext.set(ctx)
    try:
        yield
    finally:
        SecurityContext.reset(token)


def _new_task_svc():
    session = _RecordingSession()
    svc = WmsTaskAppSvc(session=session)
    svc._task_repo = _FakeTaskRepo()
    svc._inv_app_svc = _MockInvAppSvc()
    return svc, svc._task_repo, session


def _new_receiving_svc():
    session = _RecordingSession()
    svc = ReceivingAppSvc(session=session)
    svc._recv_repo = _FakeReceivingRepo()
    svc._zone_repo = _FakeZoneRepo()
    svc._pos_repo = _FakePositionRepo()
    svc._inv_app_svc = _MockInvAppSvc()
    return svc, session


# ----------------------------- T16-10a 权限模型 -----------------------------


class TestWmsPermissionModelIntegration:
    """T16-10a: 权限模型集成测试 - is_authorized 语义。"""

    def test_no_permission_is_authorized_false(self) -> None:
        """无 wms:receiving:execute 权限时 is_authorized 返回 False（拒绝前提）。"""
        tenant_id = uuid4()
        ctx = _make_ctx(tenant_id, permissions=frozenset())  # 无任何权限
        assert ctx.is_authorized("wms:receiving:execute") is False

    def test_has_permission_is_authorized_true(self) -> None:
        """持有 wms:receiving:execute 权限时 is_authorized 返回 True。"""
        tenant_id = uuid4()
        ctx = _make_ctx(
            tenant_id, permissions=frozenset({"wms:receiving:execute"})
        )
        assert ctx.is_authorized("wms:receiving:execute") is True

    def test_platform_admin_always_authorized(self) -> None:
        """平台管理员无显式权限也 is_authorized True。"""
        tenant_id = uuid4()
        ctx = _make_ctx(tenant_id, permissions=frozenset(), is_platform_admin=True)
        assert ctx.is_authorized("wms:receiving:execute") is True

    def test_different_permission_not_authorized(self) -> None:
        """持有其他权限但不持有 wms:receiving:execute 时返回 False。"""
        tenant_id = uuid4()
        ctx = _make_ctx(
            tenant_id, permissions=frozenset({"wms:space:manage", "wms:putaway:execute"})
        )
        assert ctx.is_authorized("wms:receiving:execute") is False
        assert ctx.is_authorized("wms:space:manage") is True

    def test_permission_summary_has_any(self) -> None:
        """PermissionSummary.has_any 校验任一权限存在。"""
        tenant_id = uuid4()
        ctx = _make_ctx(
            tenant_id, permissions=frozenset({"wms:picking:execute"})
        )
        assert ctx.permissions.has_any({"wms:picking:execute", "wms:receiving:execute"}) is True
        assert ctx.permissions.has_any({"wms:receiving:execute", "wms:putaway:execute"}) is False


# ----------------------------- T16-10b 跨租户与未认证拒绝 -----------------------------


class TestWmsCrossTenantAndUnauthIntegration:
    """T16-10b: 跨租户操作与未认证拒绝集成测试。"""

    async def test_cross_tenant_receiving_rejected(self) -> None:
        """tenant A 的安全上下文操作 tenant B 的收货被拒绝。"""
        tenant_a = uuid4()
        tenant_b = uuid4()
        svc, _ = _new_receiving_svc()

        with _apply_ctx(_make_ctx(tenant_a, permissions=frozenset({"wms:receiving:execute"}))):
            with pytest.raises(WMSError) as exc:
                await svc.execute_receiving(
                    tenant_id=tenant_b,
                    receiving_id=uuid4(),
                    line_id=uuid4(),
                    received_qty=10,
                    location_id=uuid4(),
                    operated_by=uuid4(),
                )
        assert exc.value.code == WMSErrorCode.CROSS_TENANT_REF_DENIED

    async def test_unauthenticated_receiving_rejected(self) -> None:
        """无安全上下文时执行收货被拒绝。"""
        tenant_id = uuid4()
        svc, _ = _new_receiving_svc()

        with pytest.raises(WMSError) as exc:
            await svc.execute_receiving(
                tenant_id=tenant_id,
                receiving_id=uuid4(),
                line_id=uuid4(),
                received_qty=10,
                location_id=uuid4(),
                operated_by=uuid4(),
            )
        assert exc.value.code == WMSErrorCode.SERVICE_UNAVAILABLE

    async def test_cross_tenant_task_claim_rejected(self) -> None:
        """tenant A 的上下文领取 tenant B 的 Task 被拒绝。"""
        tenant_a = uuid4()
        tenant_b = uuid4()
        svc, task_repo, _ = _new_task_svc()

        # 在 tenant_b 下创建并分配 Task
        with _apply_ctx(_make_ctx(tenant_b, permissions=frozenset({"wms:task:manage", "wms:task:assign"}))):
            task = await svc.create_task(
                tenant_id=tenant_b, task_type="receiving", document_id=uuid4(),
                document_type="wms_receiving",
            )
            await svc.assign_task(
                tenant_id=tenant_b, task_id=task.task_id, assignee_id=uuid4(), operated_by=uuid4()
            )

        # tenant_a 尝试领取
        with _apply_ctx(_make_ctx(tenant_a, permissions=frozenset({"wms:task:claim"}))):
            with pytest.raises(WMSError) as exc:
                await svc.claim_task(tenant_id=tenant_b, task_id=task.task_id, user_id=uuid4())
        assert exc.value.code == WMSErrorCode.CROSS_TENANT_REF_DENIED


# ----------------------------- T16-10c 越权领取 -----------------------------


class TestWmsTaskClaimAuthorizationIntegration:
    """T16-10c: 越权领取 Task 集成测试。"""

    async def test_claim_by_non_assignee_rejected(self) -> None:
        """非分配人领取 Task 被拒绝（EITP_WMS_TASK_ASSIGNMENT_DENIED）。"""
        tenant_id = uuid4()
        svc, _, _ = _new_task_svc()
        assignee = uuid4()
        attacker = uuid4()  # 非分配人

        perms = frozenset({"wms:task:manage", "wms:task:assign", "wms:task:claim"})
        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            task = await svc.create_task(
                tenant_id=tenant_id, task_type="receiving", document_id=uuid4(),
                document_type="wms_receiving",
            )
            await svc.assign_task(
                tenant_id=tenant_id, task_id=task.task_id, assignee_id=assignee, operated_by=uuid4()
            )
            # attacker 不是 assignee，领取被拒绝
            with pytest.raises(WMSError) as exc:
                await svc.claim_task(tenant_id=tenant_id, task_id=task.task_id, user_id=attacker)
        assert exc.value.code == WMSErrorCode.TASK_ASSIGNMENT_DENIED

    async def test_claim_by_non_assignee_no_audit(self) -> None:
        """越权领取不写入审计。"""
        tenant_id = uuid4()
        svc, _, session = _new_task_svc()
        assignee = uuid4()
        attacker = uuid4()

        perms = frozenset({"wms:task:manage", "wms:task:assign", "wms:task:claim"})
        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            task = await svc.create_task(
                tenant_id=tenant_id, task_type="receiving", document_id=uuid4(),
                document_type="wms_receiving",
            )
            await svc.assign_task(
                tenant_id=tenant_id, task_id=task.task_id, assignee_id=assignee, operated_by=uuid4()
            )
            session.added.clear()  # 清除分配阶段审计
            with pytest.raises(WMSError):
                await svc.claim_task(tenant_id=tenant_id, task_id=task.task_id, user_id=attacker)

        # 越权领取不产生审计
        audits = [a for a in session.added if isinstance(a, WmsOperationAuditORM)]
        assert len(audits) == 0

    async def test_claim_by_assignee_allowed(self) -> None:
        """分配人领取 Task 成功。"""
        tenant_id = uuid4()
        svc, _, _ = _new_task_svc()
        assignee = uuid4()

        perms = frozenset({"wms:task:manage", "wms:task:assign", "wms:task:claim"})
        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            task = await svc.create_task(
                tenant_id=tenant_id, task_type="receiving", document_id=uuid4(),
                document_type="wms_receiving",
            )
            await svc.assign_task(
                tenant_id=tenant_id, task_id=task.task_id, assignee_id=assignee, operated_by=uuid4()
            )
            result = await svc.claim_task(
                tenant_id=tenant_id, task_id=task.task_id, user_id=assignee
            )

        assert result["status"] == "in_progress"

    async def test_task_claim_guard_unit(self) -> None:
        """TaskClaimGuard 领取校验单元：非分配人拒绝，分配人通过。"""
        from app.domain.warehouse.services.task_claim_guard import TaskClaimGuard

        assignee = uuid4()
        attacker = uuid4()
        task_id = uuid4()

        # 非分配人拒绝
        with pytest.raises(WMSError) as exc:
            TaskClaimGuard.validate_claim(assignee, attacker, task_id)
        assert exc.value.code == WMSErrorCode.TASK_ASSIGNMENT_DENIED

        # 分配人通过
        TaskClaimGuard.validate_claim(assignee, assignee, task_id)


# ----------------------------- T16-10d DataScope 收敛 -----------------------------


class TestWmsDataScopeConvergenceIntegration:
    """T16-10d: DataScope 收敛集成测试 - 仓库级数据范围隔离。"""

    def test_user_authorized_only_w1_can_operate_w1(self) -> None:
        """仅授权仓库 W1 的用户操作 W1 时 is_subset 返回 True。"""
        tenant_id = uuid4()
        w1 = uuid4()
        user_scope = ResolvedDataScope(
            scope_type="warehouse", warehouse_ids=frozenset({w1}), access_mode=AccessMode.WRITE
        )
        request_scope = ResolvedDataScope(
            scope_type="warehouse", warehouse_ids=frozenset({w1}), access_mode=AccessMode.WRITE
        )
        assert user_scope.is_subset(request_scope) is True

    def test_user_authorized_only_w1_cannot_operate_w2(self) -> None:
        """仅授权仓库 W1 的用户操作 W2 时 is_subset 返回 False。"""
        w1 = uuid4()
        w2 = uuid4()
        user_scope = ResolvedDataScope(
            scope_type="warehouse", warehouse_ids=frozenset({w1}), access_mode=AccessMode.WRITE
        )
        request_scope = ResolvedDataScope(
            scope_type="warehouse", warehouse_ids=frozenset({w2}), access_mode=AccessMode.WRITE
        )
        assert user_scope.is_subset(request_scope) is False

    def test_user_authorized_w1_subset_w1_w2_request(self) -> None:
        """用户范围 {W1} 是请求范围 {W1,W2} 的子集时 is_subset 返回 True。"""
        w1 = uuid4()
        w2 = uuid4()
        user_scope = ResolvedDataScope(
            scope_type="warehouse", warehouse_ids=frozenset({w1}), access_mode=AccessMode.WRITE
        )
        request_scope = ResolvedDataScope(
            scope_type="warehouse", warehouse_ids=frozenset({w1, w2}), access_mode=AccessMode.WRITE
        )
        # is_subset 语义：user ⊆ request，用户范围在请求范围内
        assert user_scope.is_subset(request_scope) is True

    def test_platform_scope_subset_any(self) -> None:
        """platform scope 是任何 scope 的子集（平台管理员全量访问）。"""
        w1 = uuid4()
        platform_scope = ResolvedDataScope(scope_type="platform")
        warehouse_scope = ResolvedDataScope(
            scope_type="warehouse", warehouse_ids=frozenset({w1}), access_mode=AccessMode.WRITE
        )
        assert platform_scope.is_subset(warehouse_scope) is True

    def test_tenant_scope_not_subset_platform(self) -> None:
        """tenant scope 不是 platform scope 的子集（租户用户不能升级为平台范围）。"""
        tenant_scope = ResolvedDataScope(scope_type="tenant")
        platform_scope = ResolvedDataScope(scope_type="platform")
        assert tenant_scope.is_subset(platform_scope) is False

    def test_different_scope_types_not_subset(self) -> None:
        """不同 scope_type 之间非子集关系。"""
        w1 = uuid4()
        tenant_scope = ResolvedDataScope(scope_type="tenant")
        warehouse_scope = ResolvedDataScope(
            scope_type="warehouse", warehouse_ids=frozenset({w1}), access_mode=AccessMode.WRITE
        )
        assert tenant_scope.is_subset(warehouse_scope) is False
        assert warehouse_scope.is_subset(tenant_scope) is False

    def test_security_context_is_data_scope_subset(self) -> None:
        """SecurityContext.is_data_scope_subset 集成 DataScope 收敛。"""
        tenant_id = uuid4()
        w1 = uuid4()
        w2 = uuid4()
        # 用户仅授权 W1
        ctx = _make_ctx(
            tenant_id,
            permissions=frozenset({"wms:receiving:execute"}),
            warehouse_ids=frozenset({w1}),
            scope_type="warehouse",
        )
        # 操作 W1 的请求 scope
        w1_request = ResolvedDataScope(
            scope_type="warehouse", warehouse_ids=frozenset({w1}), access_mode=AccessMode.WRITE
        )
        # 操作 W2 的请求 scope
        w2_request = ResolvedDataScope(
            scope_type="warehouse", warehouse_ids=frozenset({w2}), access_mode=AccessMode.WRITE
        )
        assert ctx.is_data_scope_subset(w1_request) is True
        assert ctx.is_data_scope_subset(w2_request) is False

    def test_w1_user_operate_w2_should_be_denied(self) -> None:
        """仅授权 W1 的用户操作 W2 数据时 DataScope 收敛拒绝（模拟应用层检查）。"""
        tenant_id = uuid4()
        w1 = uuid4()
        w2 = uuid4()
        ctx = _make_ctx(
            tenant_id,
            permissions=frozenset({"wms:receiving:execute"}),
            warehouse_ids=frozenset({w1}),
            scope_type="warehouse",
        )
        w2_request = ResolvedDataScope(
            scope_type="warehouse", warehouse_ids=frozenset({w2}), access_mode=AccessMode.WRITE
        )
        # 应用层 DataScope 收敛检查：用户 scope 不是 W2 请求 scope 的子集，应拒绝
        with pytest.raises(WMSError) as exc:
            if not ctx.is_data_scope_subset(w2_request):
                raise WMSError(
                    WMSErrorCode.CROSS_TENANT_REF_DENIED,
                    "DataScope 收敛拒绝：用户无权操作仓库 W2",
                )
        assert exc.value.code == WMSErrorCode.CROSS_TENANT_REF_DENIED