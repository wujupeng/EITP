"""EITP-WMS T16-08 上架/拣货/调拨/发货执行全链路集成测试。

跨模块调用 PutawayAppSvc/PickingAppSvc/TransferAppSvc/ShippingAppSvc + InventoryAppSvc（mock），
验证：
- Putaway: 执行上架 → INV TRANSFER_OUT+TRANSFER_IN → Position 源减少目标增加 → 任务完成
- Picking: 可用量校验 → INV SALES_ISSUE/TRANSFER_OUT → Position 源减少
- Transfer: 同仓库校验 → 审批 → INV TRANSFER_OUT+TRANSFER_IN
- Shipping: 拣货完成校验 → 物流单号录入 → 确认发货
"""

from __future__ import annotations

from contextlib import contextmanager
from uuid import UUID, uuid4

import pytest

from app.application.warehouse.picking_app_svc import PickingAppSvc
from app.application.warehouse.putaway_app_svc import PutawayAppSvc
from app.application.warehouse.shipping_app_svc import ShippingAppSvc
from app.application.warehouse.transfer_app_svc import TransferAppSvc
from app.infrastructure.warehouse.models import (
    WmsInventoryPositionORM,
    WmsLocationORM,
    WmsPickingLineORM,
    WmsPickingTaskORM,
    WmsPutawayTaskORM,
    WmsShippingOrderORM,
    WmsTransferLineORM,
    WmsTransferOrderORM,
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


class _DummySession:
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


class _MockInvAppSvc:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.results: list[dict] = []
        self._fail_on_call: bool = False

    async def execute_transaction(self, **kwargs) -> dict:
        if self._fail_on_call:
            raise WMSError(WMSErrorCode.INV_TRANSACTION_FAILED, "INV 事务执行失败")
        self.calls.append(dict(kwargs))
        result = {
            "transaction_id": str(uuid4()),
            "id": str(uuid4()),
            "status": "completed",
            "result_ledger_id": str(uuid4()),
        }
        self.results.append(result)
        return result


class _FakeLocationRepo:
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID], WmsLocationORM] = {}

    async def get_by_id(self, session, tenant_id, location_id):
        return self._store.get((tenant_id, location_id))

    def add(self, orm: WmsLocationORM) -> WmsLocationORM:
        _ensure_id(orm, "location_id")
        self._store[(orm.tenant_id, orm.location_id)] = orm
        return orm


class _FakePositionRepo:
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID, UUID, str], WmsInventoryPositionORM] = {}
        self.upserted: list[WmsInventoryPositionORM] = []

    async def query_by_location(self, session, tenant_id, location_id):
        return [
            orm
            for (t, sku, loc, st), orm in self._store.items()
            if t == tenant_id and loc == location_id
        ]

    async def query_by_sku_location_status(self, session, tenant_id, sku_id, location_id, status):
        return self._store.get((tenant_id, sku_id, location_id, status))

    async def upsert(self, session, orm):
        _ensure_id(orm, "position_id")
        key = (orm.tenant_id, orm.sku_id, orm.location_id, orm.inventory_status)
        self._store[key] = orm
        self.upserted.append(orm)
        return orm

    def add(self, orm: WmsInventoryPositionORM) -> WmsInventoryPositionORM:
        _ensure_id(orm, "position_id")
        key = (orm.tenant_id, orm.sku_id, orm.location_id, orm.inventory_status)
        self._store[key] = orm
        return orm


class _FakePutawayRepo:
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID], WmsPutawayTaskORM] = {}

    async def get_by_id(self, session, tenant_id, putaway_id):
        return self._store.get((tenant_id, putaway_id))

    def add(self, orm: WmsPutawayTaskORM) -> WmsPutawayTaskORM:
        _ensure_id(orm, "putaway_id")
        self._store[(orm.tenant_id, orm.putaway_id)] = orm
        return orm


class _FakePickingRepo:
    def __init__(self) -> None:
        self._tasks: dict[tuple[UUID, UUID], WmsPickingTaskORM] = {}
        self._lines: dict[UUID, list[WmsPickingLineORM]] = {}

    async def get_by_id(self, session, tenant_id, picking_id):
        return self._tasks.get((tenant_id, picking_id))

    async def list_lines(self, session, tenant_id, picking_id):
        return list(self._lines.get(picking_id, []))

    def add_task(self, orm: WmsPickingTaskORM) -> WmsPickingTaskORM:
        _ensure_id(orm, "picking_id")
        self._tasks[(orm.tenant_id, orm.picking_id)] = orm
        return orm

    def add_line(self, orm: WmsPickingLineORM) -> WmsPickingLineORM:
        _ensure_id(orm, "line_id")
        self._lines.setdefault(orm.picking_task_id, []).append(orm)
        return orm


class _FakeTransferRepo:
    def __init__(self) -> None:
        self._orders: dict[tuple[UUID, UUID], WmsTransferOrderORM] = {}
        self._lines: dict[UUID, list[WmsTransferLineORM]] = {}

    async def get_by_id(self, session, tenant_id, transfer_id):
        return self._orders.get((tenant_id, transfer_id))

    async def list_lines(self, session, tenant_id, transfer_id):
        return list(self._lines.get(transfer_id, []))

    def add_order(self, orm: WmsTransferOrderORM) -> WmsTransferOrderORM:
        _ensure_id(orm, "transfer_id")
        self._orders[(orm.tenant_id, orm.transfer_id)] = orm
        return orm

    def add_line(self, orm: WmsTransferLineORM) -> WmsTransferLineORM:
        _ensure_id(orm, "line_id")
        self._lines.setdefault(orm.transfer_order_id, []).append(orm)
        return orm


class _FakeShippingRepo:
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID], WmsShippingOrderORM] = {}

    async def get_by_id(self, session, tenant_id, shipping_id):
        return self._store.get((tenant_id, shipping_id))

    def add(self, orm: WmsShippingOrderORM) -> WmsShippingOrderORM:
        _ensure_id(orm, "shipping_id")
        self._store[(orm.tenant_id, orm.shipping_id)] = orm
        return orm


class _FakeZoneRepo:
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID], WmsZoneORM] = {}

    async def get_by_id(self, session, tenant_id, zone_id):
        return self._store.get((tenant_id, zone_id))

    def add(self, orm: WmsZoneORM) -> WmsZoneORM:
        _ensure_id(orm, "zone_id")
        self._store[(orm.tenant_id, orm.zone_id)] = orm
        return orm


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


def _make_location(tenant_id: UUID, warehouse_id: UUID, code: str, status: str = "active") -> WmsLocationORM:
    return WmsLocationORM(
        tenant_id=tenant_id,
        warehouse_id=warehouse_id,
        zone_id=uuid4(),
        location_code=code,
        location_type="shelf",
        status=status,
    )


def _make_position(
    tenant_id: UUID, sku_id: UUID, warehouse_id: UUID, location_id: UUID, qty: float, status: str = "available"
) -> WmsInventoryPositionORM:
    return WmsInventoryPositionORM(
        tenant_id=tenant_id,
        sku_id=sku_id,
        warehouse_id=warehouse_id,
        location_id=location_id,
        quantity=qty,
        inventory_status=status,
    )


# ----------------------------- T16-08a 上架集成测试 -----------------------------


class TestWmsPutawayIntegration:
    """T16-08a: 上架执行全链路集成测试。"""

    def _new_svc(self):
        session = _DummySession()
        svc = PutawayAppSvc(session=session)
        putaway_repo = _FakePutawayRepo()
        pos_repo = _FakePositionRepo()
        loc_repo = _FakeLocationRepo()
        inv_mock = _MockInvAppSvc()
        svc._putaway_repo = putaway_repo
        svc._pos_repo = pos_repo
        svc._loc_repo = loc_repo
        svc._inv_app_svc = inv_mock
        return svc, putaway_repo, pos_repo, loc_repo, inv_mock, session

    async def test_putaway_invokes_transfer_out_and_in(self) -> None:
        """执行上架调用 INV TRANSFER_OUT（源库位）+ TRANSFER_IN（目标库位）。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()
        src_loc = uuid4()
        tgt_loc = uuid4()

        svc, putaway_repo, pos_repo, loc_repo, inv_mock, _ = self._new_svc()

        loc_repo.add(_make_location(tenant_id, warehouse_id, "L-TGT"))
        tgt_loc = next(iter(loc_repo._store.values())).location_id

        task = putaway_repo.add(
            WmsPutawayTaskORM(
                tenant_id=tenant_id,
                source_location_id=src_loc,
                sku_id=sku_id,
                quantity=100,
                putaway_quantity=0,
                source_document_id=uuid4(),
                status="pending",
            )
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:putaway:execute"}))):
            result = await svc.execute_putaway(
                tenant_id=tenant_id,
                putaway_id=task.putaway_id,
                target_location_id=tgt_loc,
                putaway_qty=40,
                operated_by=uuid4(),
            )

        assert len(inv_mock.calls) == 2
        assert inv_mock.calls[0]["transaction_type"] == "transfer_out"
        assert inv_mock.calls[0]["location_id"] == src_loc
        assert inv_mock.calls[1]["transaction_type"] == "transfer_in"
        assert inv_mock.calls[1]["location_id"] == tgt_loc
        assert result["putaway_qty"] == 40

    async def test_putaway_decreases_source_increases_target_position(self) -> None:
        """上架后源库位 Position 减少，目标库位 Position 增加。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()

        svc, putaway_repo, pos_repo, loc_repo, _, _ = self._new_svc()

        src_loc_orm = loc_repo.add(_make_location(tenant_id, warehouse_id, "L-SRC"))
        tgt_loc_orm = loc_repo.add(_make_location(tenant_id, warehouse_id, "L-TGT"))
        src_pos = pos_repo.add(
            _make_position(tenant_id, sku_id, warehouse_id, src_loc_orm.location_id, 100)
        )

        task = putaway_repo.add(
            WmsPutawayTaskORM(
                tenant_id=tenant_id,
                source_location_id=src_loc_orm.location_id,
                sku_id=sku_id,
                quantity=100,
                putaway_quantity=0,
                source_document_id=uuid4(),
                status="pending",
            )
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:putaway:execute"}))):
            await svc.execute_putaway(
                tenant_id=tenant_id,
                putaway_id=task.putaway_id,
                target_location_id=tgt_loc_orm.location_id,
                putaway_qty=40,
                operated_by=uuid4(),
            )

        # 源减少 40
        assert float(src_pos.quantity) == 60
        # 目标增加 40（新建 upsert）
        assert len(pos_repo.upserted) == 1
        assert float(pos_repo.upserted[0].quantity) == 40
        assert pos_repo.upserted[0].location_id == tgt_loc_orm.location_id

    async def test_putaway_completes_task_when_full_quantity(self) -> None:
        """上架达到任务总量时任务状态变为 completed。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()

        svc, putaway_repo, pos_repo, loc_repo, _, _ = self._new_svc()

        src_loc_orm = loc_repo.add(_make_location(tenant_id, warehouse_id, "L-S"))
        tgt_loc_orm = loc_repo.add(_make_location(tenant_id, warehouse_id, "L-T"))
        pos_repo.add(_make_position(tenant_id, sku_id, warehouse_id, src_loc_orm.location_id, 100))

        task = putaway_repo.add(
            WmsPutawayTaskORM(
                tenant_id=tenant_id,
                source_location_id=src_loc_orm.location_id,
                sku_id=sku_id,
                quantity=100,
                putaway_quantity=0,
                source_document_id=uuid4(),
                status="pending",
            )
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:putaway:execute"}))):
            await svc.execute_putaway(
                tenant_id=tenant_id,
                putaway_id=task.putaway_id,
                target_location_id=tgt_loc_orm.location_id,
                putaway_qty=100,
                operated_by=uuid4(),
            )

        assert task.status == "completed"
        assert task.completed_at is not None

    async def test_putaway_disabled_target_location_rejected(self) -> None:
        """目标库位停用时上架被拒绝。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()

        svc, putaway_repo, _, loc_repo, _, _ = self._new_svc()

        tgt_loc_orm = loc_repo.add(
            _make_location(tenant_id, warehouse_id, "L-DIS", status="disabled")
        )

        task = putaway_repo.add(
            WmsPutawayTaskORM(
                tenant_id=tenant_id,
                source_location_id=uuid4(),
                sku_id=sku_id,
                quantity=100,
                putaway_quantity=0,
                source_document_id=uuid4(),
                status="pending",
            )
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:putaway:execute"}))):
            with pytest.raises(WMSError) as exc:
                await svc.execute_putaway(
                    tenant_id=tenant_id,
                    putaway_id=task.putaway_id,
                    target_location_id=tgt_loc_orm.location_id,
                    putaway_qty=10,
                    operated_by=uuid4(),
                )
        assert exc.value.code == WMSErrorCode.PUTAWAY_LOCATION_DISABLED

    async def test_putaway_over_quantity_rejected(self) -> None:
        """上架数量超出任务总量被拒绝。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()

        svc, putaway_repo, _, loc_repo, _, _ = self._new_svc()

        tgt_loc_orm = loc_repo.add(_make_location(tenant_id, warehouse_id, "L-T"))

        task = putaway_repo.add(
            WmsPutawayTaskORM(
                tenant_id=tenant_id,
                source_location_id=uuid4(),
                sku_id=sku_id,
                quantity=50,
                putaway_quantity=0,
                source_document_id=uuid4(),
                status="pending",
            )
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:putaway:execute"}))):
            with pytest.raises(WMSError) as exc:
                await svc.execute_putaway(
                    tenant_id=tenant_id,
                    putaway_id=task.putaway_id,
                    target_location_id=tgt_loc_orm.location_id,
                    putaway_qty=60,
                    operated_by=uuid4(),
                )
        assert exc.value.code == WMSErrorCode.RECEIVING_OVER_RECEIVED


# ----------------------------- T16-08b 拣货集成测试 -----------------------------


class TestWmsPickingIntegration:
    """T16-08b: 拣货执行全链路集成测试。"""

    def _new_svc(self):
        session = _DummySession()
        svc = PickingAppSvc(session=session)
        picking_repo = _FakePickingRepo()
        pos_repo = _FakePositionRepo()
        inv_mock = _MockInvAppSvc()
        svc._picking_repo = picking_repo
        svc._pos_repo = pos_repo
        svc._inv_app_svc = inv_mock
        return svc, picking_repo, pos_repo, inv_mock, session

    async def test_picking_sales_invokes_sales_issue(self) -> None:
        """销售拣货调用 INV SALES_ISSUE。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()
        src_loc = uuid4()

        svc, picking_repo, pos_repo, inv_mock, _ = self._new_svc()

        task = picking_repo.add_task(
            WmsPickingTaskORM(
                tenant_id=tenant_id,
                source_order_id=uuid4(),
                source_order_type="sales",
                warehouse_id=warehouse_id,
                status="executing",
            )
        )
        line = picking_repo.add_line(
            WmsPickingLineORM(
                tenant_id=tenant_id,
                picking_task_id=task.picking_id,
                sku_id=sku_id,
                source_location_id=src_loc,
                required_quantity=50,
                picked_quantity=0,
            )
        )
        pos_repo.add(_make_position(tenant_id, sku_id, warehouse_id, src_loc, 100))

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:picking:execute"}))):
            result = await svc.execute_picking(
                tenant_id=tenant_id,
                picking_id=task.picking_id,
                line_id=line.line_id,
                picked_qty=30,
                operated_by=uuid4(),
            )

        assert len(inv_mock.calls) == 1
        assert inv_mock.calls[0]["transaction_type"] == "sales_issue"
        assert result["picked_qty"] == 30

    async def test_picking_transfer_invokes_transfer_out(self) -> None:
        """调拨拣货（source_order_type=transfer）调用 INV TRANSFER_OUT。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()
        src_loc = uuid4()

        svc, picking_repo, pos_repo, inv_mock, _ = self._new_svc()

        task = picking_repo.add_task(
            WmsPickingTaskORM(
                tenant_id=tenant_id,
                source_order_id=uuid4(),
                source_order_type="transfer",
                warehouse_id=warehouse_id,
                status="executing",
            )
        )
        line = picking_repo.add_line(
            WmsPickingLineORM(
                tenant_id=tenant_id,
                picking_task_id=task.picking_id,
                sku_id=sku_id,
                source_location_id=src_loc,
                required_quantity=50,
                picked_quantity=0,
            )
        )
        pos_repo.add(_make_position(tenant_id, sku_id, warehouse_id, src_loc, 100))

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:picking:execute"}))):
            await svc.execute_picking(
                tenant_id=tenant_id,
                picking_id=task.picking_id,
                line_id=line.line_id,
                picked_qty=20,
                operated_by=uuid4(),
            )

        assert inv_mock.calls[0]["transaction_type"] == "transfer_out"

    async def test_picking_decreases_source_position(self) -> None:
        """拣货后源库位 Position 减少。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()
        src_loc = uuid4()

        svc, picking_repo, pos_repo, _, _ = self._new_svc()

        task = picking_repo.add_task(
            WmsPickingTaskORM(
                tenant_id=tenant_id,
                source_order_id=uuid4(),
                source_order_type="sales",
                warehouse_id=warehouse_id,
                status="executing",
            )
        )
        line = picking_repo.add_line(
            WmsPickingLineORM(
                tenant_id=tenant_id,
                picking_task_id=task.picking_id,
                sku_id=sku_id,
                source_location_id=src_loc,
                required_quantity=50,
                picked_quantity=0,
            )
        )
        src_pos = pos_repo.add(_make_position(tenant_id, sku_id, warehouse_id, src_loc, 80))

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:picking:execute"}))):
            await svc.execute_picking(
                tenant_id=tenant_id,
                picking_id=task.picking_id,
                line_id=line.line_id,
                picked_qty=30,
                operated_by=uuid4(),
            )

        assert float(src_pos.quantity) == 50
        assert float(line.picked_quantity) == 30

    async def test_picking_insufficient_available_rejected(self) -> None:
        """库位可用量不足时拣货被拒绝。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()
        src_loc = uuid4()

        svc, picking_repo, pos_repo, _, _ = self._new_svc()

        task = picking_repo.add_task(
            WmsPickingTaskORM(
                tenant_id=tenant_id,
                source_order_id=uuid4(),
                source_order_type="sales",
                warehouse_id=warehouse_id,
                status="executing",
            )
        )
        line = picking_repo.add_line(
            WmsPickingLineORM(
                tenant_id=tenant_id,
                picking_task_id=task.picking_id,
                sku_id=sku_id,
                source_location_id=src_loc,
                required_quantity=100,
                picked_quantity=0,
            )
        )
        pos_repo.add(_make_position(tenant_id, sku_id, warehouse_id, src_loc, 20))  # 仅 20 可用

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:picking:execute"}))):
            with pytest.raises(WMSError) as exc:
                await svc.execute_picking(
                    tenant_id=tenant_id,
                    picking_id=task.picking_id,
                    line_id=line.line_id,
                    picked_qty=50,
                    operated_by=uuid4(),
                )
        assert exc.value.code == WMSErrorCode.PICKING_INSUFFICIENT_AVAILABLE

    async def test_picking_over_required_rejected(self) -> None:
        """拣货数量超出需求数量被拒绝。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()
        src_loc = uuid4()

        svc, picking_repo, pos_repo, _, _ = self._new_svc()

        task = picking_repo.add_task(
            WmsPickingTaskORM(
                tenant_id=tenant_id,
                source_order_id=uuid4(),
                source_order_type="sales",
                warehouse_id=warehouse_id,
                status="executing",
            )
        )
        line = picking_repo.add_line(
            WmsPickingLineORM(
                tenant_id=tenant_id,
                picking_task_id=task.picking_id,
                sku_id=sku_id,
                source_location_id=src_loc,
                required_quantity=30,
                picked_quantity=0,
            )
        )
        pos_repo.add(_make_position(tenant_id, sku_id, warehouse_id, src_loc, 100))

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:picking:execute"}))):
            with pytest.raises(WMSError) as exc:
                await svc.execute_picking(
                    tenant_id=tenant_id,
                    picking_id=task.picking_id,
                    line_id=line.line_id,
                    picked_qty=40,
                    operated_by=uuid4(),
                )
        assert exc.value.code == WMSErrorCode.PICKING_QTY_MISMATCH


# ----------------------------- T16-08c 调拨集成测试 -----------------------------


class TestWmsTransferIntegration:
    """T16-08c: 调拨执行全链路集成测试。"""

    def _new_svc(self):
        session = _DummySession()
        svc = TransferAppSvc(session=session)
        transfer_repo = _FakeTransferRepo()
        pos_repo = _FakePositionRepo()
        loc_repo = _FakeLocationRepo()
        inv_mock = _MockInvAppSvc()
        svc._transfer_repo = transfer_repo
        svc._pos_repo = pos_repo
        svc._loc_repo = loc_repo
        svc._inv_app_svc = inv_mock
        return svc, transfer_repo, pos_repo, loc_repo, inv_mock, session

    async def test_transfer_submit_approve_execute_chain(self) -> None:
        """调拨：提交审批 → 审批通过 → 执行移库 → INV TRANSFER_OUT+TRANSFER_IN。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()

        svc, transfer_repo, pos_repo, loc_repo, inv_mock, _ = self._new_svc()

        src_loc_orm = loc_repo.add(_make_location(tenant_id, warehouse_id, "L-FROM"))
        tgt_loc_orm = loc_repo.add(_make_location(tenant_id, warehouse_id, "L-TO"))
        pos_repo.add(_make_position(tenant_id, sku_id, warehouse_id, src_loc_orm.location_id, 100))

        order = transfer_repo.add_order(
            WmsTransferOrderORM(
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
                status="draft",
                require_approval=True,
            )
        )
        line = transfer_repo.add_line(
            WmsTransferLineORM(
                tenant_id=tenant_id,
                transfer_order_id=order.transfer_id,
                sku_id=sku_id,
                source_location_id=src_loc_orm.location_id,
                target_location_id=tgt_loc_orm.location_id,
                quantity=50,
                transferred_quantity=0,
            )
        )

        perms = frozenset({"wms:transfer:execute", "wms:transfer:approve"})
        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            submit_res = await svc.submit_for_approval(tenant_id=tenant_id, transfer_id=order.transfer_id)
            assert submit_res["status"] == "submitted"

            approve_res = await svc.approve(
                tenant_id=tenant_id, transfer_id=order.transfer_id, approver_id=uuid4()
            )
            assert approve_res["status"] == "approved"

            result = await svc.execute_transfer(
                tenant_id=tenant_id,
                transfer_id=order.transfer_id,
                line_id=line.line_id,
                transfer_qty=50,
                operated_by=uuid4(),
            )

        assert len(inv_mock.calls) == 2
        assert inv_mock.calls[0]["transaction_type"] == "transfer_out"
        assert inv_mock.calls[0]["location_id"] == src_loc_orm.location_id
        assert inv_mock.calls[1]["transaction_type"] == "transfer_in"
        assert inv_mock.calls[1]["location_id"] == tgt_loc_orm.location_id
        assert result["transfer_qty"] == 50

    async def test_transfer_not_approved_rejected(self) -> None:
        """需审批的调拨单未审批时执行被拒绝。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()

        svc, transfer_repo, pos_repo, loc_repo, _, _ = self._new_svc()

        src_loc_orm = loc_repo.add(_make_location(tenant_id, warehouse_id, "L-F"))
        tgt_loc_orm = loc_repo.add(_make_location(tenant_id, warehouse_id, "L-T"))

        order = transfer_repo.add_order(
            WmsTransferOrderORM(
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
                status="draft",
                require_approval=True,
            )
        )
        line = transfer_repo.add_line(
            WmsTransferLineORM(
                tenant_id=tenant_id,
                transfer_order_id=order.transfer_id,
                sku_id=sku_id,
                source_location_id=src_loc_orm.location_id,
                target_location_id=tgt_loc_orm.location_id,
                quantity=50,
                transferred_quantity=0,
            )
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:transfer:execute"}))):
            with pytest.raises(WMSError) as exc:
                await svc.execute_transfer(
                    tenant_id=tenant_id,
                    transfer_id=order.transfer_id,
                    line_id=line.line_id,
                    transfer_qty=10,
                    operated_by=uuid4(),
                )
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION

    async def test_transfer_cross_warehouse_rejected(self) -> None:
        """跨仓库移库被拒绝。"""
        tenant_id = uuid4()
        wh_a = uuid4()
        wh_b = uuid4()
        sku_id = uuid4()

        svc, transfer_repo, pos_repo, loc_repo, _, _ = self._new_svc()

        src_loc_orm = loc_repo.add(_make_location(tenant_id, wh_a, "L-A"))
        tgt_loc_orm = loc_repo.add(_make_location(tenant_id, wh_b, "L-B"))

        order = transfer_repo.add_order(
            WmsTransferOrderORM(
                tenant_id=tenant_id,
                warehouse_id=wh_a,
                status="approved",
                require_approval=False,
            )
        )
        line = transfer_repo.add_line(
            WmsTransferLineORM(
                tenant_id=tenant_id,
                transfer_order_id=order.transfer_id,
                sku_id=sku_id,
                source_location_id=src_loc_orm.location_id,
                target_location_id=tgt_loc_orm.location_id,
                quantity=50,
                transferred_quantity=0,
            )
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:transfer:execute"}))):
            with pytest.raises(WMSError) as exc:
                await svc.execute_transfer(
                    tenant_id=tenant_id,
                    transfer_id=order.transfer_id,
                    line_id=line.line_id,
                    transfer_qty=10,
                    operated_by=uuid4(),
                )
        assert exc.value.code == WMSErrorCode.TRANSFER_CROSS_WAREHOUSE

    async def test_transfer_decreases_source_increases_target(self) -> None:
        """移库后源库位减少，目标库位增加。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()

        svc, transfer_repo, pos_repo, loc_repo, _, _ = self._new_svc()

        src_loc_orm = loc_repo.add(_make_location(tenant_id, warehouse_id, "L-S"))
        tgt_loc_orm = loc_repo.add(_make_location(tenant_id, warehouse_id, "L-T"))
        src_pos = pos_repo.add(
            _make_position(tenant_id, sku_id, warehouse_id, src_loc_orm.location_id, 100)
        )

        order = transfer_repo.add_order(
            WmsTransferOrderORM(
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
                status="approved",
                require_approval=False,
            )
        )
        line = transfer_repo.add_line(
            WmsTransferLineORM(
                tenant_id=tenant_id,
                transfer_order_id=order.transfer_id,
                sku_id=sku_id,
                source_location_id=src_loc_orm.location_id,
                target_location_id=tgt_loc_orm.location_id,
                quantity=60,
                transferred_quantity=0,
            )
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:transfer:execute"}))):
            await svc.execute_transfer(
                tenant_id=tenant_id,
                transfer_id=order.transfer_id,
                line_id=line.line_id,
                transfer_qty=60,
                operated_by=uuid4(),
            )

        assert float(src_pos.quantity) == 40
        assert len(pos_repo.upserted) == 1
        assert float(pos_repo.upserted[0].quantity) == 60


# ----------------------------- T16-08d 发货集成测试 -----------------------------


class TestWmsShippingIntegration:
    """T16-08d: 发货执行全链路集成测试。"""

    def _new_svc(self):
        session = _DummySession()
        svc = ShippingAppSvc(session=session)
        shipping_repo = _FakeShippingRepo()
        zone_repo = _FakeZoneRepo()
        svc._shipping_repo = shipping_repo
        svc._zone_repo = zone_repo
        return svc, shipping_repo, zone_repo, session

    async def test_record_logistics_then_confirm_chain(self) -> None:
        """录入物流单号 → 确认发货完成全链路。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()

        svc, shipping_repo, zone_repo, session = self._new_svc()

        zone = zone_repo.add(
            WmsZoneORM(
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
                zone_code="Z-SHIP",
                zone_name="发货区",
                zone_function="shipping",
                status="active",
            )
        )
        order = shipping_repo.add(
            WmsShippingOrderORM(
                tenant_id=tenant_id,
                source_order_id=uuid4(),
                warehouse_id=warehouse_id,
                zone_id=zone.zone_id,
                status="draft",
                picking_completed=True,
            )
        )

        perms = frozenset({"wms:shipping:execute"})
        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            logistics_res = await svc.record_logistics(
                tenant_id=tenant_id,
                shipping_id=order.shipping_id,
                logistics_no="SF-20260831-001",
                logistics_company="顺丰",
                operated_by=uuid4(),
            )
            assert logistics_res["status"] == "executing"
            assert logistics_res["logistics_no"] == "SF-20260831-001"

            confirm_res = await svc.confirm_shipping(
                tenant_id=tenant_id,
                shipping_id=order.shipping_id,
                operated_by=uuid4(),
            )
            assert confirm_res["status"] == "completed"

        assert order.status == "completed"
        assert order.logistics_no == "SF-20260831-001"
        assert order.shipped_at is not None

    async def test_shipping_picking_not_completed_rejected(self) -> None:
        """拣货未完成时录入物流单号被拒绝。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()

        svc, shipping_repo, zone_repo, _ = self._new_svc()

        zone = zone_repo.add(
            WmsZoneORM(
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
                zone_code="Z-S",
                zone_name="发货区",
                zone_function="shipping",
                status="active",
            )
        )
        order = shipping_repo.add(
            WmsShippingOrderORM(
                tenant_id=tenant_id,
                source_order_id=uuid4(),
                warehouse_id=warehouse_id,
                zone_id=zone.zone_id,
                status="draft",
                picking_completed=False,  # 拣货未完成
            )
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:shipping:execute"}))):
            with pytest.raises(WMSError) as exc:
                await svc.record_logistics(
                    tenant_id=tenant_id,
                    shipping_id=order.shipping_id,
                    logistics_no="SF-X",
                    logistics_company="顺丰",
                    operated_by=uuid4(),
                )
        assert exc.value.code == WMSErrorCode.SHIPPING_PICKING_NOT_COMPLETED

    async def test_shipping_non_shipping_zone_rejected(self) -> None:
        """非发货区录入物流单号被拒绝。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()

        svc, shipping_repo, zone_repo, _ = self._new_svc()

        zone = zone_repo.add(
            WmsZoneORM(
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
                zone_code="Z-NO",
                zone_name="存储区",
                zone_function="storage",  # 非发货区
                status="active",
            )
        )
        order = shipping_repo.add(
            WmsShippingOrderORM(
                tenant_id=tenant_id,
                source_order_id=uuid4(),
                warehouse_id=warehouse_id,
                zone_id=zone.zone_id,
                status="draft",
                picking_completed=True,
            )
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:shipping:execute"}))):
            with pytest.raises(WMSError) as exc:
                await svc.record_logistics(
                    tenant_id=tenant_id,
                    shipping_id=order.shipping_id,
                    logistics_no="SF-Y",
                    logistics_company="顺丰",
                    operated_by=uuid4(),
                )
        assert exc.value.code == WMSErrorCode.SHIPPING_ZONE_INVALID

    async def test_confirm_shipping_wrong_state_rejected(self) -> None:
        """发货单非 executing 状态时确认被拒绝。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()

        svc, shipping_repo, _, _ = self._new_svc()

        order = shipping_repo.add(
            WmsShippingOrderORM(
                tenant_id=tenant_id,
                source_order_id=uuid4(),
                warehouse_id=warehouse_id,
                zone_id=uuid4(),
                status="draft",  # 非 executing
                picking_completed=True,
            )
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({"wms:shipping:execute"}))):
            with pytest.raises(WMSError) as exc:
                await svc.confirm_shipping(
                    tenant_id=tenant_id,
                    shipping_id=order.shipping_id,
                    operated_by=uuid4(),
                )
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION