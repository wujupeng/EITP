"""EITP-WMS 补充集成测试 - InventoryPositionAppSvc 查询与 ReconcileAppSvc 对账。

覆盖 WMS 库存位置多维度查询（PDA 扫码、SKU/库位/状态精确查询、状态聚合）
与 WMS↔INV 对账（差异发现、列出、解决），提升 WMS 应用服务整体覆盖率。
"""

from __future__ import annotations

from contextlib import contextmanager
from uuid import UUID, uuid4

import pytest

from app.application.warehouse.inventory_position_app_svc import InventoryPositionAppSvc
from app.application.warehouse.reconcile_app_svc import ReconcileAppSvc
from app.infrastructure.warehouse.space_repositories import LocationRepository
from app.infrastructure.warehouse.models import (
    WmsInventoryPositionORM,
    WmsLocationORM,
    WmsReconcileDiffORM,
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
    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    def add(self, _orm: object) -> None:
        return None


def _ensure_id(orm: object, attr: str) -> None:
    if getattr(orm, attr) is None:
        setattr(orm, attr, uuid4())


class _FakePositionRepo:
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID, UUID, str], WmsInventoryPositionORM] = {}

    async def query_by_sku(self, session, tenant_id, sku_id, warehouse_id=None):
        return [
            orm
            for (t, sku, loc, st), orm in self._store.items()
            if t == tenant_id and sku == sku_id and (warehouse_id is None or orm.warehouse_id == warehouse_id)
        ]

    async def query_by_location(self, session, tenant_id, location_id):
        return [
            orm
            for (t, sku, loc, st), orm in self._store.items()
            if t == tenant_id and loc == location_id
        ]

    async def query_by_sku_location_status(self, session, tenant_id, sku_id, location_id, status):
        return self._store.get((tenant_id, sku_id, location_id, status))

    async def aggregate_by_sku_warehouse(self, session, tenant_id, sku_id, warehouse_id):
        status_map: dict[str, float] = {}
        for (t, sku, loc, st), orm in self._store.items():
            if t == tenant_id and sku == sku_id and orm.warehouse_id == warehouse_id:
                status_map[st] = status_map.get(st, 0.0) + float(orm.quantity)
        return [(st, qty) for st, qty in status_map.items()]

    async def upsert(self, session, orm):
        _ensure_id(orm, "position_id")
        key = (orm.tenant_id, orm.sku_id, orm.location_id, orm.inventory_status)
        self._store[key] = orm
        return orm

    def add(self, orm):
        _ensure_id(orm, "position_id")
        key = (orm.tenant_id, orm.sku_id, orm.location_id, orm.inventory_status)
        self._store[key] = orm
        return orm


class _FakeLocationRepo:
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID], WmsLocationORM] = {}

    async def get_by_id(self, session, tenant_id, location_id):
        return self._store.get((tenant_id, location_id))

    async def get_by_code(self, session, tenant_id, warehouse_id, location_code):
        for (t, lid), orm in self._store.items():
            if (
                t == tenant_id
                and orm.warehouse_id == warehouse_id
                and orm.location_code == location_code
            ):
                return orm
        return None

    async def list_available_for_picking(self, session, tenant_id, warehouse_id):
        return [
            orm
            for (t, _lid), orm in self._store.items()
            if t == tenant_id and orm.warehouse_id == warehouse_id and orm.status == "active"
        ]

    def add(self, orm):
        _ensure_id(orm, "location_id")
        self._store[(orm.tenant_id, orm.location_id)] = orm
        return orm


class _FakeDiffRepo:
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID], WmsReconcileDiffORM] = {}
        self.saved: list[WmsReconcileDiffORM] = []

    async def save(self, session, orm):
        _ensure_id(orm, "diff_id")
        self._store[(orm.tenant_id, orm.diff_id)] = orm
        self.saved.append(orm)
        return orm

    async def list_open_diffs(self, session, tenant_id):
        return [
            orm
            for (t, _did), orm in self._store.items()
            if t == tenant_id and orm.status == "open"
        ]

    async def resolve(self, session, tenant_id, diff_id, resolution_note, resolved_at):
        orm = self._store.get((tenant_id, diff_id))
        if orm is not None:
            orm.status = "resolved"
            orm.resolution_note = resolution_note
            orm.resolved_at = resolved_at


class _MockReconcileSvc:
    """Mock 对账领域服务 - 提供 classify_diff 方法。"""

    @staticmethod
    def classify_diff(wms_qty: float, inv_qty: float) -> str:
        if wms_qty > inv_qty:
            return "wms_more"
        if inv_qty > wms_qty:
            return "inv_more"
        return "match_mismatch"


# ----------------------------- 公共辅助 -----------------------------


_WMS_POSITION_QUERY = "wms:position:query"
_WMS_RECONCILE = "wms:reconcile:execute"


def _make_ctx(tenant_id: UUID, permissions: frozenset[str] = frozenset()) -> SecurityContext:
    return SecurityContext(
        user=UserIdentity(
            user_id=uuid4(), username="wms-user", is_platform_admin=False, is_tenant_admin=True
        ),
        tenant=TenantIdentity(tenant_id=tenant_id),
        roles=(RoleSummary(role_id=uuid4(), role_code="wms_user", role_name="WMS用户"),),
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


# ----------------------------- InventoryPosition 查询测试 -----------------------------


class TestWmsInventoryPositionQueryIntegration:
    """InventoryPositionAppSvc 多维度查询集成测试。"""

    def _new_svc(self):
        session = _DummySession()
        svc = InventoryPositionAppSvc(session=session)
        pos_repo = _FakePositionRepo()
        loc_repo = _FakeLocationRepo()
        svc._pos_repo = pos_repo
        svc._loc_repo = loc_repo
        return svc, pos_repo, loc_repo

    async def test_query_by_sku(self) -> None:
        """按 SKU 查询库存位置。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()
        svc, pos_repo, _ = self._new_svc()

        pos_repo.add(_make_position(tenant_id, sku_id, warehouse_id, uuid4(), 30))
        pos_repo.add(_make_position(tenant_id, sku_id, warehouse_id, uuid4(), 20, status="in_qc"))
        pos_repo.add(_make_position(tenant_id, uuid4(), warehouse_id, uuid4(), 10))  # 其他 SKU

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_WMS_POSITION_QUERY}))):
            results = await svc.query_by_sku(tenant_id=tenant_id, sku_id=sku_id)

        assert len(results) == 2
        assert all(r["sku_id"] == str(sku_id) for r in results)

    async def test_query_by_sku_with_warehouse_filter(self) -> None:
        """按 SKU + 仓库过滤查询。"""
        tenant_id = uuid4()
        wh1 = uuid4()
        wh2 = uuid4()
        sku_id = uuid4()
        svc, pos_repo, _ = self._new_svc()

        pos_repo.add(_make_position(tenant_id, sku_id, wh1, uuid4(), 30))
        pos_repo.add(_make_position(tenant_id, sku_id, wh2, uuid4(), 20))

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_WMS_POSITION_QUERY}))):
            results = await svc.query_by_sku(tenant_id=tenant_id, sku_id=sku_id, warehouse_id=wh1)

        assert len(results) == 1
        assert results[0]["warehouse_id"] == str(wh1)

    async def test_query_by_location(self) -> None:
        """按库位查询库存位置（PDA 扫码）。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()
        location_id = uuid4()
        svc, pos_repo, _ = self._new_svc()

        pos_repo.add(_make_position(tenant_id, sku_id, warehouse_id, location_id, 50))
        pos_repo.add(_make_position(tenant_id, uuid4(), warehouse_id, uuid4(), 10))  # 其他库位

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_WMS_POSITION_QUERY}))):
            results = await svc.query_by_location(tenant_id=tenant_id, location_id=location_id)

        assert len(results) == 1
        assert results[0]["location_id"] == str(location_id)
        assert results[0]["quantity"] == 50

    async def test_query_by_location_code_pda_scan(self) -> None:
        """PDA 扫码 - 按库位编码查询库存位置。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()
        svc, pos_repo, loc_repo = self._new_svc()

        loc = loc_repo.add(
            WmsLocationORM(
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
                zone_id=uuid4(),
                location_code="A-01-02",
                location_type="shelf",
                status="active",
            )
        )
        pos_repo.add(_make_position(tenant_id, sku_id, warehouse_id, loc.location_id, 40))

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_WMS_POSITION_QUERY}))):
            results = await svc.query_by_location_code(
                tenant_id=tenant_id, warehouse_id=warehouse_id, location_code="A-01-02"
            )

        assert len(results) == 1
        assert results[0]["quantity"] == 40

    async def test_query_by_location_code_not_found_rejected(self) -> None:
        """PDA 扫码 - 库位编码不存在被拒绝。"""
        tenant_id = uuid4()
        svc, _, _ = self._new_svc()

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_WMS_POSITION_QUERY}))):
            with pytest.raises(WMSError) as exc:
                await svc.query_by_location_code(
                    tenant_id=tenant_id, warehouse_id=uuid4(), location_code="GHOST"
                )
        assert exc.value.code == WMSErrorCode.WAREHOUSE_NOT_FOUND

    async def test_query_by_sku_location_status(self) -> None:
        """按 SKU+库位+状态精确查询。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()
        location_id = uuid4()
        svc, pos_repo, _ = self._new_svc()

        pos_repo.add(_make_position(tenant_id, sku_id, warehouse_id, location_id, 30, status="available"))
        pos_repo.add(_make_position(tenant_id, sku_id, warehouse_id, location_id, 10, status="blocked"))

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_WMS_POSITION_QUERY}))):
            result = await svc.query_by_sku_location_status(
                tenant_id=tenant_id,
                sku_id=sku_id,
                location_id=location_id,
                inventory_status="available",
            )

        assert result is not None
        assert result["quantity"] == 30
        assert result["inventory_status"] == "available"

    async def test_query_by_sku_location_status_not_found(self) -> None:
        """精确查询无匹配返回 None。"""
        tenant_id = uuid4()
        svc, _, _ = self._new_svc()

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_WMS_POSITION_QUERY}))):
            result = await svc.query_by_sku_location_status(
                tenant_id=tenant_id,
                sku_id=uuid4(),
                location_id=uuid4(),
                inventory_status="available",
            )
        assert result is None

    async def test_aggregate_by_sku_warehouse(self) -> None:
        """按状态聚合 SKU 在仓库中的库存量（对账用）。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()
        svc, pos_repo, _ = self._new_svc()

        pos_repo.add(_make_position(tenant_id, sku_id, warehouse_id, uuid4(), 30, status="available"))
        pos_repo.add(_make_position(tenant_id, sku_id, warehouse_id, uuid4(), 20, status="available"))
        pos_repo.add(_make_position(tenant_id, sku_id, warehouse_id, uuid4(), 15, status="in_qc"))

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_WMS_POSITION_QUERY}))):
            result = await svc.aggregate_by_sku_warehouse(
                tenant_id=tenant_id, sku_id=sku_id, warehouse_id=warehouse_id
            )

        agg = {item["inventory_status"]: item["total_quantity"] for item in result}
        assert agg["available"] == 50
        assert agg["in_qc"] == 15

    async def test_cross_tenant_query_rejected(self) -> None:
        """跨租户查询库存位置被拒绝。"""
        tenant_a = uuid4()
        tenant_b = uuid4()
        svc, _, _ = self._new_svc()

        with _apply_ctx(_make_ctx(tenant_a, permissions=frozenset({_WMS_POSITION_QUERY}))):
            with pytest.raises(WMSError) as exc:
                await svc.query_by_sku(tenant_id=tenant_b, sku_id=uuid4())
        assert exc.value.code == WMSErrorCode.CROSS_TENANT_REF_DENIED


# ----------------------------- Reconcile 对账测试 -----------------------------


class TestWmsReconcileIntegration:
    """ReconcileAppSvc 对账集成测试。"""

    def _new_svc(self):
        session = _DummySession()
        svc = ReconcileAppSvc(session=session)
        pos_repo = _FakePositionRepo()
        diff_repo = _FakeDiffRepo()
        svc._pos_repo = pos_repo
        svc._diff_repo = diff_repo
        svc._reconcile_svc = _MockReconcileSvc()
        return svc, pos_repo, diff_repo

    async def test_run_reconcile_detects_diff(self) -> None:
        """对账发现 WMS 与 INV 差异并记录。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()
        svc, pos_repo, diff_repo = self._new_svc()

        # 注入 LocationRepository 到 svc（run_reconcile 内部新建 LocationRepository）
        loc_repo = _FakeLocationRepo()
        loc_repo.add(
            WmsLocationORM(
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
                zone_id=uuid4(),
                location_code="L-1",
                location_type="shelf",
                status="active",
            )
        )
        # run_reconcile 内部局部导入 LocationRepository，通过 patch 源模块类方法注入
        loc_orm = list(loc_repo._store.values())[0]
        pos_repo.add(_make_position(tenant_id, sku_id, warehouse_id, loc_orm.location_id, 100))

        # INV 侧 available=80，WMS 侧 available=100，差异 20
        def inv_provider(t, sku, wh):
            return {"available": 80}

        # patch LocationRepository.list_available_for_picking
        from unittest.mock import patch

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_WMS_RECONCILE}))):
            with patch.object(
                LocationRepository, "list_available_for_picking", new=loc_repo.list_available_for_picking
            ):
                diffs = await svc.run_reconcile(
                    tenant_id=tenant_id,
                    warehouse_id=warehouse_id,
                    inv_balance_provider=inv_provider,
                )

        assert len(diffs) == 1
        assert diffs[0]["wms_quantity"] == 100
        assert diffs[0]["inv_quantity"] == 80
        assert diffs[0]["diff_quantity"] == 20
        assert diffs[0]["diff_type"] == "wms_more"
        assert len(diff_repo.saved) == 1

    async def test_run_reconcile_no_diff_when_consistent(self) -> None:
        """WMS 与 INV 一致时对账无差异。"""
        tenant_id = uuid4()
        warehouse_id = uuid4()
        sku_id = uuid4()
        svc, pos_repo, diff_repo = self._new_svc()

        loc_repo = _FakeLocationRepo()
        loc_repo.add(
            WmsLocationORM(
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
                zone_id=uuid4(),
                location_code="L-C",
                location_type="shelf",
                status="active",
            )
        )
        loc_orm = list(loc_repo._store.values())[0]
        pos_repo.add(_make_position(tenant_id, sku_id, warehouse_id, loc_orm.location_id, 50))

        def inv_provider(t, sku, wh):
            return {"available": 50}

        from unittest.mock import patch

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_WMS_RECONCILE}))):
            with patch.object(
                LocationRepository, "list_available_for_picking", new=loc_repo.list_available_for_picking
            ):
                diffs = await svc.run_reconcile(
                    tenant_id=tenant_id,
                    warehouse_id=warehouse_id,
                    inv_balance_provider=inv_provider,
                )

        assert len(diffs) == 0
        assert len(diff_repo.saved) == 0

    async def test_list_open_diffs(self) -> None:
        """查询未解决的对账差异。"""
        tenant_id = uuid4()
        svc, _, diff_repo = self._new_svc()

        diff_repo._store[(tenant_id, uuid4())] = WmsReconcileDiffORM(
            tenant_id=tenant_id,
            sku_id=uuid4(),
            warehouse_id=uuid4(),
            wms_quantity=100,
            inv_quantity=80,
            diff_quantity=20,
            diff_type="wms_more",
            status="open",
        )
        diff_repo._store[(tenant_id, uuid4())] = WmsReconcileDiffORM(
            tenant_id=tenant_id,
            sku_id=uuid4(),
            warehouse_id=uuid4(),
            wms_quantity=50,
            inv_quantity=50,
            diff_quantity=0,
            diff_type="match_mismatch",
            status="resolved",
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_WMS_RECONCILE}))):
            diffs = await svc.list_open_diffs(tenant_id=tenant_id)

        assert len(diffs) == 1
        assert diffs[0]["status"] == "open"

    async def test_resolve_diff(self) -> None:
        """解决对账差异。"""
        tenant_id = uuid4()
        svc, _, diff_repo = self._new_svc()

        diff_id = uuid4()
        diff = WmsReconcileDiffORM(
            tenant_id=tenant_id,
            sku_id=uuid4(),
            warehouse_id=uuid4(),
            wms_quantity=100,
            inv_quantity=80,
            diff_quantity=20,
            diff_type="wms_more",
            status="open",
        )
        _ensure_id(diff, "diff_id")
        diff_id = diff.diff_id
        diff_repo._store[(tenant_id, diff_id)] = diff

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_WMS_RECONCILE}))):
            result = await svc.resolve_diff(
                tenant_id=tenant_id,
                diff_id=diff_id,
                resolution_note="以 INV 为准调整",
                operated_by=uuid4(),
            )

        assert result["status"] == "resolved"
        assert diff.status == "resolved"
        assert diff.resolution_note == "以 INV 为准调整"

    async def test_cross_tenant_reconcile_rejected(self) -> None:
        """跨租户对账被拒绝。"""
        tenant_a = uuid4()
        tenant_b = uuid4()
        svc, _, _ = self._new_svc()

        with _apply_ctx(_make_ctx(tenant_a, permissions=frozenset({_WMS_RECONCILE}))):
            with pytest.raises(WMSError) as exc:
                await svc.list_open_diffs(tenant_id=tenant_b)
        assert exc.value.code == WMSErrorCode.CROSS_TENANT_REF_DENIED