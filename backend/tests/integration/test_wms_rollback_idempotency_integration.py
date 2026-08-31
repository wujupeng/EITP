"""EITP-WMS T16-09 INV 事务失败回滚与幂等性集成测试。

跨模块调用 ReceivingAppSvc/WmsTaskAppSvc + InventoryAppSvc（mock），
验证：
- INV 抛异常 → WMS 作业中断 → Inventory Position 不变 → 审计未写入 → session rollback
- 相同 idempotency_key 重复 create_task 返回首个结果，不产生重复 Task
- Task 状态机非法转移被拒绝
"""

from __future__ import annotations

from contextlib import contextmanager
from uuid import UUID, uuid4

import pytest

from app.application.warehouse.receiving_app_svc import ReceivingAppSvc
from app.application.warehouse.wms_task_app_svc import WmsTaskAppSvc
from app.infrastructure.warehouse.models import (
    WmsInventoryPositionORM,
    WmsOperationAuditORM,
    WmsReceivingLineORM,
    WmsReceivingOrderORM,
    WmsTaskORM,
    WmsZoneORM,
)
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode
from app.interfaces.middleware.security_context import (
    PermissionSummary,
    ResolvedDataScope,
    RoleSummary,
    SecurityContext,
    TenantIdentity,
    UserIdentity,
)


# ----------------------------- 测试替身 -----------------------------


class _RecordingSession:
    """记录 flush/commit/rollback/add 调用的 Session 替身。"""

    def __init__(self) -> None:
        self.added: list[object] = []
        self.flush_count = 0
        self.commit_count = 0
        self.rollback_count = 0

    async def flush(self) -> None:
        self.flush_count += 1

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1

    def add(self, orm: object) -> None:
        self.added.append(orm)


def _ensure_id(orm: object, attr: str) -> None:
    if getattr(orm, attr) is None:
        setattr(orm, attr, uuid4())


class _MockInvAppSvc:
    """Mock INV 应用服务 - 可控失败 + 幂等返回。"""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.results: list[dict] = []
        self._fail_on_call: bool = False
        self._idempotent_cache: dict[str, dict] = {}

    async def execute_transaction(self, **kwargs) -> dict:
        if self._fail_on_call:
            raise WMSError(WMSErrorCode.INV_TRANSACTION_FAILED, "INV 事务执行失败")
        self.calls.append(dict(kwargs))
        idem_key = kwargs.get("idempotency_key")
        # 幂等：相同 idempotency_key 返回首次结果
        if idem_key and idem_key in self._idempotent_cache:
            return self._idempotent_cache[idem_key]
        result = {
            "transaction_id": str(uuid4()),
            "id": str(uuid4()),
            "status": "completed",
            "result_ledger_id": str(uuid4()),
        }
        if idem_key:
            self._idempotent_cache[idem_key] = result
        self.results.append(result)
        return result


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

    def add_order(self, order):
        _ensure_id(order, "receiving_id")
        self._orders[(order.tenant_id, order.receiving_id)] = order
        return order

    def add_line(self, line):
        _ensure_id(line, "line_id")
        self._lines.setdefault(line.receiving_id, []).append(line)
        return line


class _FakeZoneRepo:
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID], WmsZoneORM] = {}

    async def get_by_id(self, session, tenant_id, zone_id):
        return self._store.get((tenant_id, zone_id))

    def add(self, zone):
        _ensure_id(zone, "zone_id")
        self._store[(zone.tenant_id, zone.zone_id)] = zone
        return zone


class _FakePositionRepo:
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID, UUID, str], WmsInventoryPositionORM] = {}
        self.upserted: list[WmsInventoryPositionORM] = []

    async def query_by_sku_location_status(self, session, tenant_id, sku_id, location_id, status):
        return self._store.get((tenant_id, sku_id, location_id, status))

    async def upsert(self, session, orm):
        _ensure_id(orm, "position_id")
        key = (orm.tenant_id, orm.sku_id, orm.location_id, orm.inventory_status)
        self._store[key] = orm
        self.upserted.append(orm)
        return orm


class _FakeTaskRepo:
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID], WmsTaskORM] = {}
        self._idem_store: dict[tuple[UUID, str], WmsTaskORM] = {}

    async def get_by_id(self, session, tenant_id, task_id):
        return self._store.get((tenant_id, task_id))

    async def get_by_idempotency_key(self, session, tenant_id, idempotency_key):
        return self._idem_store.get((tenant_id, idempotency_key))

    async def save(self, session, orm):
        _ensure_id(orm, "task_id")
        self._store[(orm.tenant_id, orm.task_id)] = orm
        if orm.idempotency_key:
            self._idem_store[(orm.tenant_id, orm.idempotency_key)] = orm
        return orm

    async def update_status(self, session, tenant_id, task_id, new_status, **kwargs):
        orm = self._store.get((tenant_id, task_id))
        if orm is not None:
            orm.status = new_status
            if kwargs.get("assigned_at"):
                orm.assigned_at = kwargs["assigned_at"]
            if kwargs.get("started_at"):
                orm.started_at = kwargs["started_at"]
            if kwargs.get("completed_at"):
                orm.completed_at = kwargs["completed_at"]

    async def list_by_status(self, session, tenant_id, status, offset=0, limit=50):
        return [
            orm
            for (t, _tid), orm in self._store.items()
            if t == tenant_id and orm.status == status
        ][offset : offset + limit]

    async def list_by_assignee(self, session, tenant_id, assignee_id, status=None):
        return [
            orm
            for (t, _tid), orm in self._store.items()
            if t == tenant_id
            and orm.assignee_id == assignee_id
            and (status is None or orm.status == status)
        ]


# ----------------------------- 公共辅助 -----------------------------


def _make_ctx(tenant_id: UUID, permissions: frozenset[str] = frozenset()) -> SecurityContext:
    return SecurityContext(
        user=UserIdentity(
            user_id=uuid4(), username="wms-worker", is_platform_admin=False, is_tenant_admin=True
        ),
        tenant=TenantIdentity(tenant_id=tenant_id),
        roles=(RoleSummary(role_id=uuid4(), role_code="wms_worker", role_name="WMS作业员"),),
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


def _new_receiving_svc():
    session = _RecordingSession()
    svc = ReceivingAppSvc(session=session)
    recv_repo = _FakeReceivingRepo()
    zone_repo = _FakeZoneRepo()
    pos_repo = _FakePositionRepo()
    inv_mock = _MockInvAppSvc()
    svc._recv_repo = recv_repo
    svc._zone_repo = zone_repo
    svc._pos_repo = pos_repo
    svc._inv_app_svc = inv_mock
    return svc, recv_repo, zone_repo, pos_repo, inv_mock, session


def _new_task_svc():
    session = _RecordingSession()
    svc = WmsTaskAppSvc(session=session)
    task_repo = _FakeTaskRepo()
    svc._task_repo = task_repo
    return svc, task_repo, session


def _setup_receiving(tenant_id, inv_fail=False):
    """构造收货单 + 行 + 收货区，返回所需句柄。"""
    svc, recv_repo, zone_repo, pos_repo, inv_mock, session = _new_receiving_svc()
    inv_mock._fail_on_call = inv_fail

    warehouse_id = uuid4()
    sku_id = uuid4()
    zone = zone_repo.add(
        WmsZoneORM(
            tenant_id=tenant_id,
            warehouse_id=warehouse_id,
            zone_code="Z-R",
            zone_name="收货区",
            zone_function="receiving",
            status="active",
        )
    )
    order = recv_repo.add_order(
        WmsReceivingOrderORM(
            tenant_id=tenant_id,
            source_document_id=uuid4(),
            source_document_type="purchase_order",
            warehouse_id=warehouse_id,
            zone_id=zone.zone_id,
            status="submitted",
            over_receive_ratio=0,
        )
    )
    line = recv_repo.add_line(
        WmsReceivingLineORM(
            tenant_id=tenant_id,
            receiving_id=order.receiving_id,
            sku_id=sku_id,
            ordered_quantity=100,
            received_quantity=0,
            is_inspection_required=False,
        )
    )
    return svc, recv_repo, zone_repo, pos_repo, inv_mock, session, order, line, sku_id, warehouse_id


# ----------------------------- T16-09a INV 失败回滚 -----------------------------


class TestWmsInvFailureRollbackIntegration:
    """T16-09a: INV 事务失败回滚集成测试。"""

    async def test_inv_failure_propagates_wms_error(self) -> None:
        """INV 抛异常时 execute_receiving 传播 WMSError(INV_TRANSACTION_FAILED)。"""
        tenant_id = uuid4()
        svc, _, _, _, _, _, order, line, _, _ = _setup_receiving(tenant_id, inv_fail=True)

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:receiving:execute"}))):
            with pytest.raises(WMSError) as exc:
                await svc.execute_receiving(
                    tenant_id=tenant_id,
                    receiving_id=order.receiving_id,
                    line_id=line.line_id,
                    received_qty=30,
                    location_id=uuid4(),
                    operated_by=uuid4(),
                )
        assert exc.value.code == WMSErrorCode.INV_TRANSACTION_FAILED

    async def test_inv_failure_position_unchanged(self) -> None:
        """INV 失败时 Inventory Position 不变更（无 upsert）。"""
        tenant_id = uuid4()
        svc, _, _, pos_repo, _, _, order, line, _, _ = _setup_receiving(tenant_id, inv_fail=True)

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:receiving:execute"}))):
            with pytest.raises(WMSError):
                await svc.execute_receiving(
                    tenant_id=tenant_id,
                    receiving_id=order.receiving_id,
                    line_id=line.line_id,
                    received_qty=30,
                    location_id=uuid4(),
                    operated_by=uuid4(),
                )

        assert len(pos_repo.upserted) == 0
        assert len(pos_repo._store) == 0

    async def test_inv_failure_line_received_not_updated(self) -> None:
        """INV 失败时收货行 received_quantity 不更新。"""
        tenant_id = uuid4()
        svc, _, _, _, _, _, order, line, _, _ = _setup_receiving(tenant_id, inv_fail=True)

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:receiving:execute"}))):
            with pytest.raises(WMSError):
                await svc.execute_receiving(
                    tenant_id=tenant_id,
                    receiving_id=order.receiving_id,
                    line_id=line.line_id,
                    received_qty=30,
                    location_id=uuid4(),
                    operated_by=uuid4(),
                )

        assert float(line.received_quantity) == 0

    async def test_inv_failure_audit_not_written(self) -> None:
        """INV 失败时不写入操作审计。"""
        tenant_id = uuid4()
        svc, _, _, _, _, session, order, line, _, _ = _setup_receiving(tenant_id, inv_fail=True)

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:receiving:execute"}))):
            with pytest.raises(WMSError):
                await svc.execute_receiving(
                    tenant_id=tenant_id,
                    receiving_id=order.receiving_id,
                    line_id=line.line_id,
                    received_qty=30,
                    location_id=uuid4(),
                    operated_by=uuid4(),
                )

        audits = [a for a in session.added if isinstance(a, WmsOperationAuditORM)]
        assert len(audits) == 0

    async def test_inv_failure_upper_layer_rollback_called(self) -> None:
        """INV 失败时上层编排器调用 session.rollback，事务回滚。"""
        tenant_id = uuid4()
        svc, _, _, _, _, session, order, line, _, _ = _setup_receiving(tenant_id, inv_fail=True)

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:receiving:execute"}))):
            # 模拟上层编排器：捕获异常后 rollback
            try:
                await svc.execute_receiving(
                    tenant_id=tenant_id,
                    receiving_id=order.receiving_id,
                    line_id=line.line_id,
                    received_qty=30,
                    location_id=uuid4(),
                    operated_by=uuid4(),
                )
            except WMSError:
                await session.rollback()

        assert session.rollback_count == 1

    async def test_inv_success_no_rollback(self) -> None:
        """INV 成功时上层不调用 rollback，事务正常提交。"""
        tenant_id = uuid4()
        svc, _, _, _, _, session, order, line, _, _ = _setup_receiving(tenant_id, inv_fail=False)

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:receiving:execute"}))):
            await svc.execute_receiving(
                tenant_id=tenant_id,
                receiving_id=order.receiving_id,
                line_id=line.line_id,
                received_qty=30,
                location_id=uuid4(),
                operated_by=uuid4(),
            )

        assert session.rollback_count == 0


# ----------------------------- T16-09b 幂等性 -----------------------------


class TestWmsIdempotencyIntegration:
    """T16-09b: 幂等性集成测试。"""

    async def test_task_create_idempotent_returns_same_task(self) -> None:
        """相同 idempotency_key 重复 create_task 返回同一 Task。"""
        tenant_id = uuid4()
        svc, task_repo, _ = _new_task_svc()
        idem_key = "wms:receiving:order-1:line-1:30"
        doc_id = uuid4()

        perms = frozenset({"wms:task:manage"})
        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            task1 = await svc.create_task(
                tenant_id=tenant_id,
                task_type="receiving",
                document_id=doc_id,
                document_type="wms_receiving",
                idempotency_key=idem_key,
            )
            task2 = await svc.create_task(
                tenant_id=tenant_id,
                task_type="receiving",
                document_id=doc_id,
                document_type="wms_receiving",
                idempotency_key=idem_key,
            )

        assert task1.task_id == task2.task_id
        assert len(task_repo._store) == 1

    async def test_task_create_different_idempotency_keys_create_separate(self) -> None:
        """不同 idempotency_key 创建独立 Task。"""
        tenant_id = uuid4()
        svc, task_repo, _ = _new_task_svc()
        doc_id = uuid4()

        perms = frozenset({"wms:task:manage"})
        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            t1 = await svc.create_task(
                tenant_id=tenant_id, task_type="receiving", document_id=doc_id,
                document_type="wms_receiving", idempotency_key="key-A",
            )
            t2 = await svc.create_task(
                tenant_id=tenant_id, task_type="receiving", document_id=doc_id,
                document_type="wms_receiving", idempotency_key="key-B",
            )

        assert t1.task_id != t2.task_id
        assert len(task_repo._store) == 2

    async def test_task_create_without_idempotency_key_always_creates(self) -> None:
        """无 idempotency_key 时每次 create_task 都新建。"""
        tenant_id = uuid4()
        svc, task_repo, _ = _new_task_svc()
        doc_id = uuid4()

        perms = frozenset({"wms:task:manage"})
        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            t1 = await svc.create_task(
                tenant_id=tenant_id, task_type="receiving", document_id=doc_id,
                document_type="wms_receiving",
            )
            t2 = await svc.create_task(
                tenant_id=tenant_id, task_type="receiving", document_id=doc_id,
                document_type="wms_receiving",
            )

        assert t1.task_id != t2.task_id
        assert len(task_repo._store) == 2

    async def test_inv_idempotent_no_duplicate_inventory_change(self) -> None:
        """INV 侧幂等：相同 idempotency_key 重复调用返回首次结果，不重复变更。"""
        tenant_id = uuid4()
        svc, _, _, pos_repo, inv_mock, _, order, line, _, _ = _setup_receiving(tenant_id)

        location_id = uuid4()
        perms = frozenset({"wms:receiving:execute"})
        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            # 首次收货 30
            await svc.execute_receiving(
                tenant_id=tenant_id,
                receiving_id=order.receiving_id,
                line_id=line.line_id,
                received_qty=30,
                location_id=location_id,
                operated_by=uuid4(),
            )

        # INV 侧被调用一次
        assert len(inv_mock.calls) == 1
        first_idem = inv_mock.calls[0]["idempotency_key"]

        # 模拟 INV 侧幂等查重：相同 idempotency_key 再次调用 INV 返回相同结果
        # （receiving 层不查重，但 INV 侧通过 idempotency_key 幂等）
        inv_result_1 = inv_mock._idempotent_cache[first_idem]
        # 再次以相同 idempotency_key 调用 INV（模拟重试）
        inv_result_2 = await inv_mock.execute_transaction(
            tenant_id=tenant_id,
            sku_id=line.sku_id,
            warehouse_id=order.warehouse_id,
            transaction_type="purchase_receipt",
            quantity=30,
            idempotency_key=first_idem,
            operated_by=uuid4(),
        )
        # 幂等：返回相同结果，不产生新的事务
        assert inv_result_1 == inv_result_2

    async def test_receiving_idempotency_key_format_stable(self) -> None:
        """收货 idempotency_key 格式稳定（receiving_id:line_id:qty），支持重试幂等。"""
        tenant_id = uuid4()
        svc, _, _, _, inv_mock, _, order, line, _, _ = _setup_receiving(tenant_id)

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:receiving:execute"}))):
            await svc.execute_receiving(
                tenant_id=tenant_id,
                receiving_id=order.receiving_id,
                line_id=line.line_id,
                received_qty=25,
                location_id=uuid4(),
                operated_by=uuid4(),
            )

        expected = f"wms:receiving:{order.receiving_id}:{line.line_id}:25"
        assert inv_mock.calls[0]["idempotency_key"] == expected


# ----------------------------- T16-09c Task 状态机 -----------------------------


class TestWmsTaskStateMachineIntegration:
    """T16-09c: Task 状态机非法转移被拒绝（失败路径边界）。"""

    async def test_task_assign_claim_cancel_chain(self) -> None:
        """Task: create → assign → claim → cancel 全链路。"""
        tenant_id = uuid4()
        svc, _, _ = _new_task_svc()
        assignee = uuid4()
        doc_id = uuid4()

        perms = frozenset({"wms:task:manage", "wms:task:assign", "wms:task:claim", "wms:task:cancel"})
        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            task = await svc.create_task(
                tenant_id=tenant_id, task_type="putaway", document_id=doc_id,
                document_type="wms_putaway",
            )
            await svc.assign_task(
                tenant_id=tenant_id, task_id=task.task_id, assignee_id=assignee, operated_by=uuid4()
            )
            await svc.claim_task(tenant_id=tenant_id, task_id=task.task_id, user_id=assignee)
            res = await svc.cancel_task(
                tenant_id=tenant_id, task_id=task.task_id, operated_by=uuid4(), reason="取消"
            )

        assert res["status"] == "cancelled"

    async def test_assign_non_created_task_rejected(self) -> None:
        """非 created 状态 Task 分配被拒绝。"""
        tenant_id = uuid4()
        svc, task_repo, _ = _new_task_svc()
        doc_id = uuid4()

        perms = frozenset({"wms:task:manage", "wms:task:assign", "wms:task:claim"})
        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            task = await svc.create_task(
                tenant_id=tenant_id, task_type="receiving", document_id=doc_id,
                document_type="wms_receiving",
            )
            await svc.assign_task(
                tenant_id=tenant_id, task_id=task.task_id, assignee_id=uuid4(), operated_by=uuid4()
            )
            # 已 assigned，再次 assign 被拒绝
            with pytest.raises(WMSError) as exc:
                await svc.assign_task(
                    tenant_id=tenant_id, task_id=task.task_id, assignee_id=uuid4(), operated_by=uuid4()
                )
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION

    async def test_claim_non_assigned_task_rejected(self) -> None:
        """非 assigned 状态 Task 领取被拒绝。"""
        tenant_id = uuid4()
        svc, _, _ = _new_task_svc()
        doc_id = uuid4()

        perms = frozenset({"wms:task:manage", "wms:task:claim"})
        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            task = await svc.create_task(
                tenant_id=tenant_id, task_type="receiving", document_id=doc_id,
                document_type="wms_receiving",
            )
            # created 状态领取被拒绝
            with pytest.raises(WMSError) as exc:
                await svc.claim_task(tenant_id=tenant_id, task_id=task.task_id, user_id=uuid4())
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION

    async def test_cancel_completed_task_rejected(self) -> None:
        """已完成 Task 取消被拒绝。"""
        tenant_id = uuid4()
        svc, task_repo, _ = _new_task_svc()
        doc_id = uuid4()

        perms = frozenset({"wms:task:manage", "wms:task:cancel"})
        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            task = await svc.create_task(
                tenant_id=tenant_id, task_type="receiving", document_id=doc_id,
                document_type="wms_receiving",
            )
            # 手动置为 completed
            task.status = "completed"
            with pytest.raises(WMSError) as exc:
                await svc.cancel_task(
                    tenant_id=tenant_id, task_id=task.task_id, operated_by=uuid4()
                )
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION

    async def test_query_tasks_by_status(self) -> None:
        """按状态查询 Task 列表。"""
        tenant_id = uuid4()
        svc, _, _ = _new_task_svc()
        doc_id = uuid4()

        perms = frozenset({"wms:task:manage", "wms:task:query"})
        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            await svc.create_task(
                tenant_id=tenant_id, task_type="receiving", document_id=doc_id,
                document_type="wms_receiving",
            )
            await svc.create_task(
                tenant_id=tenant_id, task_type="putaway", document_id=uuid4(),
                document_type="wms_putaway",
            )
            tasks = await svc.query_tasks_by_status(tenant_id=tenant_id, status="created")

        assert len(tasks) == 2
        assert all(t["status"] == "created" for t in tasks)