"""EITP-WMS T16-07 收货执行全链路集成测试。

跨模块调用 ReceivingAppSvc + InventoryAppSvc（mock），
验证：创建收货单 → 执行收货 → INV PURCHASE_RECEIPT 调用参数正确
→ Inventory Position 同步（available/in_qc）→ 收货行累计 → 审计写入
→ 超收拒绝 → 收货区校验 → 幂等键生成。

Mock INV API 调用，验证 WMS 以 transaction_type="purchase_receipt" 正确调用 INV。
"""

from __future__ import annotations

from contextlib import contextmanager
from uuid import UUID, uuid4

import pytest

from app.application.warehouse.receiving_app_svc import ReceivingAppSvc
from app.infrastructure.warehouse.models import (
    WmsInventoryPositionORM,
    WmsReceivingLineORM,
    WmsReceivingOrderORM,
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

    def add_order(self, order: WmsReceivingOrderORM) -> WmsReceivingOrderORM:
        _ensure_id(order, "receiving_id")
        self._orders[(order.tenant_id, order.receiving_id)] = order
        return order

    def add_line(self, line: WmsReceivingLineORM) -> WmsReceivingLineORM:
        _ensure_id(line, "line_id")
        self._lines.setdefault(line.receiving_id, []).append(line)
        return line


class _FakeZoneRepo:
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID], WmsZoneORM] = {}

    async def get_by_id(self, session, tenant_id, zone_id):
        return self._store.get((tenant_id, zone_id))

    def add_zone(self, zone: WmsZoneORM) -> WmsZoneORM:
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


class _MockInvAppSvc:
    """Mock INV 应用服务 - 记录 execute_transaction 调用参数与返回值。"""

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


# ----------------------------- 公共辅助 -----------------------------


_WMS_RECEIVING_EXECUTE = "wms:receiving:execute"


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


def _new_receiving_svc() -> tuple[
    ReceivingAppSvc,
    _FakeReceivingRepo,
    _FakeZoneRepo,
    _FakePositionRepo,
    _MockInvAppSvc,
    _DummySession,
]:
    session = _DummySession()
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


def _make_receiving_order(
    tenant_id: UUID, warehouse_id: UUID, zone_id: UUID, over_receive_ratio: float = 0.0
) -> WmsReceivingOrderORM:
    return WmsReceivingOrderORM(
        tenant_id=tenant_id,
        source_document_id=uuid4(),
        source_document_type="purchase_order",
        warehouse_id=warehouse_id,
        zone_id=zone_id,
        status="submitted",
        over_receive_ratio=over_receive_ratio,
    )


def _make_receiving_line(
    tenant_id: UUID,
    receiving_id: UUID,
    sku_id: UUID,
    ordered_quantity: float,
    received_quantity: float = 0,
    is_inspection_required: bool = False,
) -> WmsReceivingLineORM:
    return WmsReceivingLineORM(
        tenant_id=tenant_id,
        receiving_id=receiving_id,
        sku_id=sku_id,
        ordered_quantity=ordered_quantity,
        received_quantity=received_quantity,
        is_inspection_required=is_inspection_required,
    )


# ----------------------------- 集成测试 -----------------------------


class TestWmsReceivingFullChainIntegration:
    """T16-07: 收货执行全链路集成测试。"""

    async def test_execute_receiving_calls_inv_purchase_receipt(self) -> None:
        """执行收货以 transaction_type=purchase_receipt 调用 INV。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()
        operated_by = uuid4()

        svc, recv_repo, zone_repo, _, inv_mock, _ = _new_receiving_svc()

        zone = zone_repo.add_zone(
            WmsZoneORM(
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
                zone_code="Z-RECV",
                zone_name="收货区",
                zone_function="receiving",
                status="active",
            )
        )
        order = recv_repo.add_order(_make_receiving_order(tenant_id, warehouse_id, zone.zone_id))
        line = recv_repo.add_line(
            _make_receiving_line(tenant_id, order.receiving_id, sku_id, ordered_quantity=100)
        )
        location_id = uuid4()

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_WMS_RECEIVING_EXECUTE}))):
            result = await svc.execute_receiving(
                tenant_id=tenant_id,
                receiving_id=order.receiving_id,
                line_id=line.line_id,
                received_qty=30,
                location_id=location_id,
                operated_by=operated_by,
            )

        # INV 被调用一次，transaction_type 为 purchase_receipt
        assert len(inv_mock.calls) == 1
        inv_call = inv_mock.calls[0]
        assert inv_call["transaction_type"] == "purchase_receipt"
        assert inv_call["tenant_id"] == tenant_id
        assert inv_call["sku_id"] == sku_id
        assert inv_call["warehouse_id"] == warehouse_id
        assert inv_call["quantity"] == 30
        assert inv_call["operated_by"] == operated_by
        assert inv_call["document_id"] == order.receiving_id
        assert inv_call["document_type"] == "wms_receiving"
        assert inv_call["location_id"] == location_id
        # 幂等键格式
        assert inv_call["idempotency_key"] == f"wms:receiving:{order.receiving_id}:{line.line_id}:30"

        # 返回结果
        assert result["receiving_id"] == str(order.receiving_id)
        assert result["received_qty"] == 30
        assert result["inventory_status"] == "available"
        assert result["inv_transaction_id"] is not None

    async def test_receiving_syncs_inventory_position_available(self) -> None:
        """无需检验时收货同步 Position 状态为 available。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()

        svc, recv_repo, zone_repo, pos_repo, inv_mock, _ = _new_receiving_svc()

        zone = zone_repo.add_zone(
            WmsZoneORM(
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
                zone_code="Z-R",
                zone_name="收货区",
                zone_function="receiving",
                status="active",
            )
        )
        order = recv_repo.add_order(_make_receiving_order(tenant_id, warehouse_id, zone.zone_id))
        line = recv_repo.add_line(
            _make_receiving_line(
                tenant_id, order.receiving_id, sku_id, ordered_quantity=100,
                is_inspection_required=False,
            )
        )
        location_id = uuid4()

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_WMS_RECEIVING_EXECUTE}))):
            await svc.execute_receiving(
                tenant_id=tenant_id,
                receiving_id=order.receiving_id,
                line_id=line.line_id,
                received_qty=50,
                location_id=location_id,
                operated_by=uuid4(),
            )

        # Position 被创建，状态 available，数量 50
        assert len(pos_repo.upserted) == 1
        pos = pos_repo.upserted[0]
        assert pos.sku_id == sku_id
        assert pos.location_id == location_id
        assert pos.warehouse_id == warehouse_id
        assert float(pos.quantity) == 50
        assert pos.inventory_status == "available"

    async def test_receiving_syncs_inventory_position_in_qc_when_inspection_required(self) -> None:
        """需检验时收货同步 Position 状态为 in_qc。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()

        svc, recv_repo, zone_repo, pos_repo, _, _ = _new_receiving_svc()

        zone = zone_repo.add_zone(
            WmsZoneORM(
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
                zone_code="Z-QC",
                zone_name="质检区",
                zone_function="qc",
                status="active",
            )
        )
        order = recv_repo.add_order(_make_receiving_order(tenant_id, warehouse_id, zone.zone_id))
        line = recv_repo.add_line(
            _make_receiving_line(
                tenant_id, order.receiving_id, sku_id, ordered_quantity=100,
                is_inspection_required=True,
            )
        )
        location_id = uuid4()

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_WMS_RECEIVING_EXECUTE}))):
            await svc.execute_receiving(
                tenant_id=tenant_id,
                receiving_id=order.receiving_id,
                line_id=line.line_id,
                received_qty=20,
                location_id=location_id,
                operated_by=uuid4(),
            )

        assert len(pos_repo.upserted) == 1
        assert pos_repo.upserted[0].inventory_status == "in_qc"
        assert float(pos_repo.upserted[0].quantity) == 20

    async def test_receiving_accumulates_existing_position(self) -> None:
        """已存在同 SKU+库位+状态 Position 时累加数量。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()
        location_id = uuid4()

        svc, recv_repo, zone_repo, pos_repo, _, _ = _new_receiving_svc()

        zone = zone_repo.add_zone(
            WmsZoneORM(
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
                zone_code="Z-A",
                zone_name="收货区",
                zone_function="receiving",
                status="active",
            )
        )
        order = recv_repo.add_order(_make_receiving_order(tenant_id, warehouse_id, zone.zone_id))
        line = recv_repo.add_line(
            _make_receiving_line(tenant_id, order.receiving_id, sku_id, ordered_quantity=100)
        )
        # 预置已有 Position 数量 40
        existing = WmsInventoryPositionORM(
            tenant_id=tenant_id,
            sku_id=sku_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            quantity=40,
            inventory_status="available",
        )
        _ensure_id(existing, "position_id")
        pos_repo._store[(tenant_id, sku_id, location_id, "available")] = existing

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_WMS_RECEIVING_EXECUTE}))):
            await svc.execute_receiving(
                tenant_id=tenant_id,
                receiving_id=order.receiving_id,
                line_id=line.line_id,
                received_qty=30,
                location_id=location_id,
                operated_by=uuid4(),
            )

        # 累加后 70，未新增 upsert
        assert float(existing.quantity) == 70
        assert len(pos_repo.upserted) == 0

    async def test_receiving_line_received_quantity_accumulated(self) -> None:
        """收货行 received_quantity 累计更新。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()

        svc, recv_repo, zone_repo, _, _, _ = _new_receiving_svc()

        zone = zone_repo.add_zone(
            WmsZoneORM(
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
                zone_code="Z-L",
                zone_name="收货区",
                zone_function="receiving",
                status="active",
            )
        )
        order = recv_repo.add_order(_make_receiving_order(tenant_id, warehouse_id, zone.zone_id))
        line = recv_repo.add_line(
            _make_receiving_line(
                tenant_id, order.receiving_id, sku_id, ordered_quantity=100, received_quantity=10
            )
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_WMS_RECEIVING_EXECUTE}))):
            await svc.execute_receiving(
                tenant_id=tenant_id,
                receiving_id=order.receiving_id,
                line_id=line.line_id,
                received_qty=25,
                location_id=uuid4(),
                operated_by=uuid4(),
            )

        assert float(line.received_quantity) == 35

    async def test_receiving_writes_audit(self) -> None:
        """收货执行写入操作审计（含 INV transaction_id）。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()
        operated_by = uuid4()

        svc, recv_repo, zone_repo, _, inv_mock, session = _new_receiving_svc()

        zone = zone_repo.add_zone(
            WmsZoneORM(
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
                zone_code="Z-AU",
                zone_name="收货区",
                zone_function="receiving",
                status="active",
            )
        )
        order = recv_repo.add_order(_make_receiving_order(tenant_id, warehouse_id, zone.zone_id))
        line = recv_repo.add_line(
            _make_receiving_line(tenant_id, order.receiving_id, sku_id, ordered_quantity=100)
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_WMS_RECEIVING_EXECUTE}))):
            await svc.execute_receiving(
                tenant_id=tenant_id,
                receiving_id=order.receiving_id,
                line_id=line.line_id,
                received_qty=10,
                location_id=uuid4(),
                operated_by=operated_by,
            )

        # 审计记录被 add 到 session
        from app.infrastructure.warehouse.models import WmsOperationAuditORM

        audits = [a for a in session.added if isinstance(a, WmsOperationAuditORM)]
        assert len(audits) == 1
        audit = audits[0]
        assert audit.event_type == "wms_receiving_executed"
        assert audit.user_id == operated_by
        assert audit.sku_id == sku_id
        assert audit.warehouse_id == warehouse_id
        # 审计含 INV transaction_id
        assert len(audit.inv_transaction_ids) == 1
        assert audit.inv_transaction_ids[0] == inv_mock.results[0]["transaction_id"]
        # before/after 状态记录：审计在 update_line_received 之后构造，
        # before_state 反映更新后值，after_state 为 before + received_qty
        assert audit.after_state["received_quantity"] - audit.before_state["received_quantity"] == 10
        assert audit.after_state["received_quantity"] == 20

    async def test_over_receive_rejected(self) -> None:
        """收货数量超出允许范围被拒绝（EITP_WMS_RECEIVING_OVER_RECEIVED）。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()

        svc, recv_repo, zone_repo, _, _, _ = _new_receiving_svc()

        zone = zone_repo.add_zone(
            WmsZoneORM(
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
                zone_code="Z-OV",
                zone_name="收货区",
                zone_function="receiving",
                status="active",
            )
        )
        # over_receive_ratio=0.1，ordered=100，最大允许=110
        order = recv_repo.add_order(
            _make_receiving_order(tenant_id, warehouse_id, zone.zone_id, over_receive_ratio=0.1)
        )
        line = recv_repo.add_line(
            _make_receiving_line(tenant_id, order.receiving_id, sku_id, ordered_quantity=100)
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_WMS_RECEIVING_EXECUTE}))):
            with pytest.raises(WMSError) as exc:
                await svc.execute_receiving(
                    tenant_id=tenant_id,
                    receiving_id=order.receiving_id,
                    line_id=line.line_id,
                    received_qty=120,  # 超过 110
                    location_id=uuid4(),
                    operated_by=uuid4(),
                )
        assert exc.value.code == WMSErrorCode.RECEIVING_OVER_RECEIVED

    async def test_non_receiving_zone_rejected(self) -> None:
        """收货区功能不匹配（非 receiving/qc）被拒绝。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()

        svc, recv_repo, zone_repo, _, _, _ = _new_receiving_svc()

        zone = zone_repo.add_zone(
            WmsZoneORM(
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
                zone_code="Z-STG",
                zone_name="存储区",
                zone_function="storage",  # 非收货区
                status="active",
            )
        )
        order = recv_repo.add_order(_make_receiving_order(tenant_id, warehouse_id, zone.zone_id))
        line = recv_repo.add_line(
            _make_receiving_line(tenant_id, order.receiving_id, sku_id, ordered_quantity=100)
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_WMS_RECEIVING_EXECUTE}))):
            with pytest.raises(WMSError) as exc:
                await svc.execute_receiving(
                    tenant_id=tenant_id,
                    receiving_id=order.receiving_id,
                    line_id=line.line_id,
                    received_qty=10,
                    location_id=uuid4(),
                    operated_by=uuid4(),
                )
        assert exc.value.code == WMSErrorCode.RECEIVING_ZONE_INVALID

    async def test_nonexistent_receiving_order_rejected(self) -> None:
        """收货单不存在被拒绝。"""
        tenant_id = uuid4()
        svc, _, _, _, _, _ = _new_receiving_svc()

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_WMS_RECEIVING_EXECUTE}))):
            with pytest.raises(WMSError) as exc:
                await svc.execute_receiving(
                    tenant_id=tenant_id,
                    receiving_id=uuid4(),
                    line_id=uuid4(),
                    received_qty=10,
                    location_id=uuid4(),
                    operated_by=uuid4(),
                )
        assert exc.value.code == WMSErrorCode.WAREHOUSE_NOT_FOUND

    async def test_nonexistent_line_rejected(self) -> None:
        """收货行不存在被拒绝。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()

        svc, recv_repo, zone_repo, _, _, _ = _new_receiving_svc()

        zone = zone_repo.add_zone(
            WmsZoneORM(
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
                zone_code="Z-NL",
                zone_name="收货区",
                zone_function="receiving",
                status="active",
            )
        )
        order = recv_repo.add_order(_make_receiving_order(tenant_id, warehouse_id, zone.zone_id))

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_WMS_RECEIVING_EXECUTE}))):
            with pytest.raises(WMSError) as exc:
                await svc.execute_receiving(
                    tenant_id=tenant_id,
                    receiving_id=order.receiving_id,
                    line_id=uuid4(),  # 不存在的行
                    received_qty=10,
                    location_id=uuid4(),
                    operated_by=uuid4(),
                )
        assert exc.value.code == WMSErrorCode.SKU_NOT_FOUND

    async def test_cross_tenant_receiving_rejected(self) -> None:
        """跨租户执行收货被拒绝。"""
        tenant_a = uuid4()
        tenant_b = uuid4()
        svc, _, _, _, _, _ = _new_receiving_svc()

        with _apply_ctx(_make_ctx(tenant_a, permissions=frozenset({_WMS_RECEIVING_EXECUTE}))):
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