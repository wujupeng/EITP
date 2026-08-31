"""EITP-WMS T16-06 空间管理 CRUD 集成测试。

跨模块调用 SpaceAppSvc + HierarchyCycleGuard，
验证：创建 Warehouse/Zone/Area/Location → 重复编码拒绝 → 层级循环拒绝
→ RLS 租户隔离（tenant A 不可见 tenant B）→ 空间树查询。

对应 spec 空间管理章节，design 空间层级无环 + RLS 行级隔离。
"""

from __future__ import annotations

from contextlib import contextmanager
from uuid import UUID, uuid4

import pytest

from app.application.warehouse.space_app_svc import SpaceAppSvc
from app.domain.warehouse.aggregates.warehouse_aggregate import WarehouseStatusEnum
from app.domain.warehouse.services.hierarchy_cycle_guard import HierarchyCycleGuard
from app.infrastructure.warehouse.models import (
    WmsAreaORM,
    WmsBinORM,
    WmsEquipmentORM,
    WmsLocationORM,
    WmsWarehouseORM,
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
    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    def add(self, _orm: object) -> None:
        return None


def _ensure_id(orm: object, attr: str) -> None:
    """确保 ORM 主键 ID 存在（SQLAlchemy default 在 flush 时才生效）。"""
    if getattr(orm, attr) is None:
        setattr(orm, attr, uuid4())


class _FakeWarehouseRepo:
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID], WmsWarehouseORM] = {}

    async def get_by_id(self, session, tenant_id, warehouse_id):
        return self._store.get((tenant_id, warehouse_id))

    async def get_by_code(self, session, tenant_id, warehouse_code):
        for (t, _wid), orm in self._store.items():
            if t == tenant_id and orm.warehouse_code == warehouse_code:
                return orm
        return None

    async def list_by_tenant(self, session, tenant_id, offset=0, limit=50):
        items = [orm for (t, _wid), orm in self._store.items() if t == tenant_id]
        return items[offset : offset + limit]

    async def save(self, session, orm):
        _ensure_id(orm, "warehouse_id")
        self._store[(orm.tenant_id, orm.warehouse_id)] = orm
        return orm


class _FakeZoneRepo:
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID], WmsZoneORM] = {}

    async def get_by_id(self, session, tenant_id, zone_id):
        return self._store.get((tenant_id, zone_id))

    async def get_by_code(self, session, tenant_id, warehouse_id, zone_code):
        for (t, zid), orm in self._store.items():
            if (
                t == tenant_id
                and orm.warehouse_id == warehouse_id
                and orm.zone_code == zone_code
            ):
                return orm
        return None

    async def list_by_warehouse(self, session, tenant_id, warehouse_id):
        return [
            orm
            for (t, _zid), orm in self._store.items()
            if t == tenant_id and orm.warehouse_id == warehouse_id
        ]

    async def save(self, session, orm):
        _ensure_id(orm, "zone_id")
        self._store[(orm.tenant_id, orm.zone_id)] = orm
        return orm


class _FakeAreaRepo:
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID], WmsAreaORM] = {}

    async def get_by_id(self, session, tenant_id, area_id):
        return self._store.get((tenant_id, area_id))

    async def list_by_zone(self, session, tenant_id, zone_id):
        return [
            orm
            for (t, _aid), orm in self._store.items()
            if t == tenant_id and orm.zone_id == zone_id
        ]

    async def save(self, session, orm):
        _ensure_id(orm, "area_id")
        self._store[(orm.tenant_id, orm.area_id)] = orm
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

    async def list_by_zone(self, session, tenant_id, zone_id):
        return [
            orm
            for (t, _lid), orm in self._store.items()
            if t == tenant_id and orm.zone_id == zone_id
        ]

    async def list_available_for_putaway(self, session, tenant_id, warehouse_id):
        return [
            orm
            for (t, _lid), orm in self._store.items()
            if t == tenant_id
            and orm.warehouse_id == warehouse_id
            and orm.status == "active"
            and orm.location_type in ("floor", "shelf")
        ]

    async def list_available_for_picking(self, session, tenant_id, warehouse_id):
        return [
            orm
            for (t, _lid), orm in self._store.items()
            if t == tenant_id
            and orm.warehouse_id == warehouse_id
            and orm.status == "active"
        ]

    async def save(self, session, orm):
        _ensure_id(orm, "location_id")
        self._store[(orm.tenant_id, orm.location_id)] = orm
        return orm


class _FakeBinRepo:
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID], WmsBinORM] = {}

    async def get_by_id(self, session, tenant_id, bin_id):
        return self._store.get((tenant_id, bin_id))

    async def save(self, session, orm):
        _ensure_id(orm, "bin_id")
        self._store[(orm.tenant_id, orm.bin_id)] = orm
        return orm


class _FakeEquipmentRepo:
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID], WmsEquipmentORM] = {}

    async def get_by_id(self, session, tenant_id, equipment_id):
        return self._store.get((tenant_id, equipment_id))

    async def save(self, session, orm):
        _ensure_id(orm, "equipment_id")
        self._store[(orm.tenant_id, orm.equipment_id)] = orm
        return orm


# ----------------------------- 公共辅助 -----------------------------


_WMS_SPACE_MANAGE = "wms:space:manage"
_WMS_SPACE_QUERY = "wms:space:query"


def _make_ctx(
    tenant_id: UUID,
    permissions: frozenset[str] = frozenset(),
    is_platform_admin: bool = False,
) -> SecurityContext:
    return SecurityContext(
        user=UserIdentity(
            user_id=uuid4(),
            username="wms-admin",
            is_platform_admin=is_platform_admin,
            is_tenant_admin=True,
        ),
        tenant=TenantIdentity(tenant_id=tenant_id),
        roles=(RoleSummary(role_id=uuid4(), role_code="wms_admin", role_name="WMS管理员"),),
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


def _new_space_svc() -> tuple[
    SpaceAppSvc, _FakeWarehouseRepo, _FakeZoneRepo, _FakeAreaRepo, _FakeLocationRepo, _FakeBinRepo, _FakeEquipmentRepo
]:
    svc = SpaceAppSvc(session=_DummySession())
    wh_repo = _FakeWarehouseRepo()
    zone_repo = _FakeZoneRepo()
    area_repo = _FakeAreaRepo()
    loc_repo = _FakeLocationRepo()
    bin_repo = _FakeBinRepo()
    equip_repo = _FakeEquipmentRepo()
    svc._wh_repo = wh_repo
    svc._zone_repo = zone_repo
    svc._area_repo = area_repo
    svc._loc_repo = loc_repo
    svc._bin_repo = bin_repo
    svc._equip_repo = equip_repo
    return svc, wh_repo, zone_repo, area_repo, loc_repo, bin_repo, equip_repo


# ----------------------------- 集成测试 -----------------------------


class TestWmsSpaceCrudIntegration:
    """T16-06: 空间管理 CRUD 集成测试。"""

    async def test_create_warehouse_zone_area_location_chain(self) -> None:
        """创建 Warehouse → Zone → Area → Location 全链路成功。"""
        tenant_id = uuid4()
        svc, wh_repo, zone_repo, area_repo, loc_repo, _, _ = _new_space_svc()
        perms = frozenset({_WMS_SPACE_MANAGE, _WMS_SPACE_QUERY})

        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            wh = await svc.create_warehouse(
                tenant_id=tenant_id,
                warehouse_code="WH-001",
                warehouse_name="主仓库",
            )
            assert wh.warehouse_code == "WH-001"
            assert wh.status == WarehouseStatusEnum.ACTIVE.value

            zone = await svc.create_zone(
                tenant_id=tenant_id,
                warehouse_id=wh.warehouse_id,
                zone_code="Z-STORAGE",
                zone_name="存储区",
                zone_function="storage",
            )
            assert zone.zone_code == "Z-STORAGE"
            assert zone.warehouse_id == wh.warehouse_id

            area = await svc.create_area(
                tenant_id=tenant_id,
                zone_id=zone.zone_id,
                area_code="A-01",
                area_name="A区",
            )
            assert area.area_code == "A-01"

            loc = await svc.create_location(
                tenant_id=tenant_id,
                warehouse_id=wh.warehouse_id,
                zone_id=zone.zone_id,
                location_code="L-01",
                location_type="shelf",
                area_id=area.area_id,
                capacity_max_qty=1000,
            )
            assert loc.location_code == "L-01"
            assert loc.status == "active"

        # 仓储持久化验证
        assert await wh_repo.get_by_id(None, tenant_id, wh.warehouse_id) is not None
        assert await zone_repo.get_by_id(None, tenant_id, zone.zone_id) is not None
        assert await area_repo.get_by_id(None, tenant_id, area.area_id) is not None
        assert await loc_repo.get_by_id(None, tenant_id, loc.location_id) is not None

    async def test_duplicate_warehouse_code_rejected(self) -> None:
        """同一租户重复仓库编码被拒绝（EITP_WMS_LOCATION_CODE_DUPLICATE）。"""
        tenant_id = uuid4()
        svc, _, _, _, _, _, _ = _new_space_svc()
        perms = frozenset({_WMS_SPACE_MANAGE})

        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            await svc.create_warehouse(
                tenant_id=tenant_id,
                warehouse_code="WH-DUP",
                warehouse_name="仓库1",
            )
            with pytest.raises(WMSError) as exc:
                await svc.create_warehouse(
                    tenant_id=tenant_id,
                    warehouse_code="WH-DUP",
                    warehouse_name="仓库2",
                )
        assert exc.value.code == WMSErrorCode.LOCATION_CODE_DUPLICATE

    async def test_duplicate_zone_code_rejected(self) -> None:
        """同一仓库内重复库区编码被拒绝。"""
        tenant_id = uuid4()
        svc, _, _, _, _, _, _ = _new_space_svc()
        perms = frozenset({_WMS_SPACE_MANAGE})

        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            wh = await svc.create_warehouse(
                tenant_id=tenant_id, warehouse_code="WH-Z", warehouse_name="仓库Z"
            )
            await svc.create_zone(
                tenant_id=tenant_id,
                warehouse_id=wh.warehouse_id,
                zone_code="Z-01",
                zone_name="区1",
            )
            with pytest.raises(WMSError) as exc:
                await svc.create_zone(
                    tenant_id=tenant_id,
                    warehouse_id=wh.warehouse_id,
                    zone_code="Z-01",
                    zone_name="区1重复",
                )
        assert exc.value.code == WMSErrorCode.LOCATION_CODE_DUPLICATE

    async def test_duplicate_location_code_rejected(self) -> None:
        """同一仓库内重复库位编码被拒绝。"""
        tenant_id = uuid4()
        svc, _, _, _, _, _, _ = _new_space_svc()
        perms = frozenset({_WMS_SPACE_MANAGE})

        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            wh = await svc.create_warehouse(
                tenant_id=tenant_id, warehouse_code="WH-L", warehouse_name="仓库L"
            )
            zone = await svc.create_zone(
                tenant_id=tenant_id,
                warehouse_id=wh.warehouse_id,
                zone_code="ZL",
                zone_name="区",
            )
            await svc.create_location(
                tenant_id=tenant_id,
                warehouse_id=wh.warehouse_id,
                zone_id=zone.zone_id,
                location_code="LOC-01",
            )
            with pytest.raises(WMSError) as exc:
                await svc.create_location(
                    tenant_id=tenant_id,
                    warehouse_id=wh.warehouse_id,
                    zone_id=zone.zone_id,
                    location_code="LOC-01",
                )
        assert exc.value.code == WMSErrorCode.LOCATION_CODE_DUPLICATE

    async def test_create_zone_nonexistent_warehouse_rejected(self) -> None:
        """库区指向不存在的仓库被拒绝。"""
        tenant_id = uuid4()
        svc, _, _, _, _, _, _ = _new_space_svc()
        perms = frozenset({_WMS_SPACE_MANAGE})

        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            with pytest.raises(WMSError) as exc:
                await svc.create_zone(
                    tenant_id=tenant_id,
                    warehouse_id=uuid4(),
                    zone_code="Z-GHOST",
                    zone_name="幽灵区",
                )
        assert exc.value.code == WMSErrorCode.WAREHOUSE_NOT_FOUND

    async def test_create_zone_disabled_warehouse_rejected(self) -> None:
        """仓库已停用时创建库区被拒绝。"""
        tenant_id = uuid4()
        svc, _, _, _, _, _, _ = _new_space_svc()
        perms = frozenset({_WMS_SPACE_MANAGE})

        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            wh = await svc.create_warehouse(
                tenant_id=tenant_id, warehouse_code="WH-DIS", warehouse_name="停用仓库"
            )
            wh.status = WarehouseStatusEnum.DISABLED.value
            with pytest.raises(WMSError) as exc:
                await svc.create_zone(
                    tenant_id=tenant_id,
                    warehouse_id=wh.warehouse_id,
                    zone_code="Z-X",
                    zone_name="区",
                )
        assert exc.value.code == WMSErrorCode.WAREHOUSE_DISABLED

    async def test_create_bin(self) -> None:
        """创建料箱成功。"""
        tenant_id = uuid4()
        svc, _, _, _, loc_repo, bin_repo, _ = _new_space_svc()
        perms = frozenset({_WMS_SPACE_MANAGE})

        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            wh = await svc.create_warehouse(
                tenant_id=tenant_id, warehouse_code="WH-B", warehouse_name="仓库"
            )
            zone = await svc.create_zone(
                tenant_id=tenant_id, warehouse_id=wh.warehouse_id, zone_code="Z-B", zone_name="区"
            )
            loc = await svc.create_location(
                tenant_id=tenant_id, warehouse_id=wh.warehouse_id, zone_id=zone.zone_id,
                location_code="L-B",
            )
            bin_orm = await svc.create_bin(
                tenant_id=tenant_id, location_id=loc.location_id, bin_code="BIN-01"
            )

        assert bin_orm.bin_code == "BIN-01"
        assert bin_orm.status == "active"
        assert await bin_repo.get_by_id(None, tenant_id, bin_orm.bin_id) is not None

    async def test_create_equipment(self) -> None:
        """创建设备成功。"""
        tenant_id = uuid4()
        svc, _, _, _, _, _, equip_repo = _new_space_svc()
        perms = frozenset({_WMS_SPACE_MANAGE})

        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            wh = await svc.create_warehouse(
                tenant_id=tenant_id, warehouse_code="WH-E", warehouse_name="仓库"
            )
            equip = await svc.create_equipment(
                tenant_id=tenant_id, warehouse_id=wh.warehouse_id,
                equipment_code="EQ-01", equipment_type="forklift",
            )

        assert equip.equipment_code == "EQ-01"
        assert equip.equipment_type == "forklift"
        assert equip.status == "active"
        assert await equip_repo.get_by_id(None, tenant_id, equip.equipment_id) is not None

    async def test_toggle_location_status(self) -> None:
        """切换库位状态：停用后再启用。"""
        tenant_id = uuid4()
        svc, _, _, _, _, _, _ = _new_space_svc()
        perms = frozenset({_WMS_SPACE_MANAGE})

        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            wh = await svc.create_warehouse(
                tenant_id=tenant_id, warehouse_code="WH-TL", warehouse_name="仓库"
            )
            zone = await svc.create_zone(
                tenant_id=tenant_id, warehouse_id=wh.warehouse_id, zone_code="Z-TL", zone_name="区"
            )
            loc = await svc.create_location(
                tenant_id=tenant_id, warehouse_id=wh.warehouse_id, zone_id=zone.zone_id,
                location_code="L-TL",
            )
            assert loc.status == "active"

            disabled = await svc.toggle_location_status(
                tenant_id=tenant_id, location_id=loc.location_id, activate=False
            )
            assert disabled.status == "disabled"

            enabled = await svc.toggle_location_status(
                tenant_id=tenant_id, location_id=loc.location_id, activate=True
            )
            assert enabled.status == "active"


class TestWmsHierarchyCycleIntegration:
    """T16-06: 空间层级无环校验集成测试。"""

    def test_validate_no_cycle_passes(self) -> None:
        """无环层级关系通过校验。"""
        a, b, c = uuid4(), uuid4(), uuid4()
        parent_map = {a: None, b: a, c: b}
        HierarchyCycleGuard.validate(parent_map)  # 不抛异常即通过

    def test_validate_cycle_rejected(self) -> None:
        """含循环引用的层级关系被拒绝（EITP_WMS_HIERARCHY_CYCLE）。"""
        a, b = uuid4(), uuid4()
        parent_map = {a: b, b: a}
        with pytest.raises(WMSError) as exc:
            HierarchyCycleGuard.validate(parent_map)
        assert exc.value.code == WMSErrorCode.HIERARCHY_CYCLE

    def test_self_loop_rejected(self) -> None:
        """自环引用被拒绝。"""
        a = uuid4()
        parent_map = {a: a}
        with pytest.raises(WMSError) as exc:
            HierarchyCycleGuard.validate(parent_map)
        assert exc.value.code == WMSErrorCode.HIERARCHY_CYCLE

    def test_move_to_self_rejected(self) -> None:
        """将节点移动到自身之下被拒绝。"""
        a, b = uuid4(), uuid4()
        parent_map = {a: None, b: a}
        with pytest.raises(WMSError) as exc:
            HierarchyCycleGuard.validate_move(parent_map, b, b)
        assert exc.value.code == WMSErrorCode.HIERARCHY_CYCLE

    def test_move_to_descendant_rejected(self) -> None:
        """将节点移动到其后代之下形成循环被拒绝。"""
        # 层级: a -> b -> c (a 是根, b 是 a 的子, c 是 b 的子)
        a, b, c = uuid4(), uuid4(), uuid4()
        parent_map = {a: None, b: a, c: b}
        # 将 a 移动到 c 下会形成 a->c->b->a 循环
        with pytest.raises(WMSError) as exc:
            HierarchyCycleGuard.validate_move(parent_map, a, c)
        assert exc.value.code == WMSErrorCode.HIERARCHY_CYCLE

    def test_move_to_non_descendant_allowed(self) -> None:
        """将节点移动到非后代下不形成循环，通过校验。"""
        a, b, c = uuid4(), uuid4(), uuid4()
        parent_map = {a: None, b: a, c: a}
        # 将 b 移动到 c 下，b 和 c 是兄弟，不形成循环
        HierarchyCycleGuard.validate_move(parent_map, b, c)


class TestWmsSpaceRlsTenantIsolationIntegration:
    """T16-06: RLS 租户隔离集成测试 - tenant A 不可见 tenant B。"""

    async def test_same_warehouse_code_allowed_across_tenants(self) -> None:
        """不同租户可使用相同仓库编码（RLS 行级隔离）。"""
        tenant_a = uuid4()
        tenant_b = uuid4()
        svc, wh_repo, _, _, _, _, _ = _new_space_svc()
        perms = frozenset({_WMS_SPACE_MANAGE})

        with _apply_ctx(_make_ctx(tenant_a, permissions=perms)):
            wh_a = await svc.create_warehouse(
                tenant_id=tenant_a, warehouse_code="WH-SHARED", warehouse_name="A仓库"
            )
        with _apply_ctx(_make_ctx(tenant_b, permissions=perms)):
            wh_b = await svc.create_warehouse(
                tenant_id=tenant_b, warehouse_code="WH-SHARED", warehouse_name="B仓库"
            )

        # 两个租户各自拥有独立仓库
        assert wh_a.warehouse_id != wh_b.warehouse_id
        assert wh_a.tenant_id == tenant_a
        assert wh_b.tenant_id == tenant_b

    async def test_tenant_a_cannot_see_tenant_b_warehouse(self) -> None:
        """tenant A 的仓储查询看不到 tenant B 的仓库。"""
        tenant_a = uuid4()
        tenant_b = uuid4()
        svc, wh_repo, _, _, _, _, _ = _new_space_svc()
        perms = frozenset({_WMS_SPACE_MANAGE, _WMS_SPACE_QUERY})

        with _apply_ctx(_make_ctx(tenant_a, permissions=perms)):
            wh_a = await svc.create_warehouse(
                tenant_id=tenant_a, warehouse_code="WH-A", warehouse_name="A仓库"
            )
        with _apply_ctx(_make_ctx(tenant_b, permissions=perms)):
            await svc.create_warehouse(
                tenant_id=tenant_b, warehouse_code="WH-B", warehouse_name="B仓库"
            )

        # tenant A 查询 tenant B 的仓库返回 None（RLS 过滤）
        assert await wh_repo.get_by_id(None, tenant_a, wh_a.warehouse_id) is not None
        assert await wh_repo.get_by_id(None, tenant_b, wh_a.warehouse_id) is None
        # tenant A 按编码查询只看到自己的
        a_by_code = await wh_repo.get_by_code(None, tenant_a, "WH-B")
        assert a_by_code is None

    async def test_cross_tenant_operation_rejected(self) -> None:
        """tenant A 的安全上下文操作 tenant B 的数据被拒绝。"""
        tenant_a = uuid4()
        tenant_b = uuid4()
        svc, _, _, _, _, _, _ = _new_space_svc()
        perms = frozenset({_WMS_SPACE_MANAGE})

        with _apply_ctx(_make_ctx(tenant_a, permissions=perms)):
            with pytest.raises(WMSError) as exc:
                await svc.create_warehouse(
                    tenant_id=tenant_b,  # 操作目标租户 B
                    warehouse_code="WH-CROSS",
                    warehouse_name="跨租户",
                )
        assert exc.value.code == WMSErrorCode.CROSS_TENANT_REF_DENIED

    async def test_cross_tenant_query_space_tree_rejected(self) -> None:
        """tenant A 查询 tenant B 的空间树被拒绝。"""
        tenant_a = uuid4()
        tenant_b = uuid4()
        svc, wh_repo, _, _, _, _, _ = _new_space_svc()
        perms = frozenset({_WMS_SPACE_MANAGE, _WMS_SPACE_QUERY})

        with _apply_ctx(_make_ctx(tenant_b, permissions=perms)):
            wh_b = await svc.create_warehouse(
                tenant_id=tenant_b, warehouse_code="WH-B", warehouse_name="B仓库"
            )

        with _apply_ctx(_make_ctx(tenant_a, permissions=perms)):
            with pytest.raises(WMSError) as exc:
                await svc.query_space_tree(tenant_id=tenant_b, warehouse_id=wh_b.warehouse_id)
        assert exc.value.code == WMSErrorCode.CROSS_TENANT_REF_DENIED

    async def test_unauthenticated_rejected(self) -> None:
        """无安全上下文时操作被拒绝。"""
        tenant_id = uuid4()
        svc, _, _, _, _, _, _ = _new_space_svc()

        with pytest.raises(WMSError) as exc:
            await svc.create_warehouse(
                tenant_id=tenant_id, warehouse_code="WH-NOCTX", warehouse_name="无上下文"
            )
        assert exc.value.code == WMSErrorCode.SERVICE_UNAVAILABLE


class TestWmsSpaceTreeQueryIntegration:
    """T16-06: 空间树查询集成测试。"""

    async def test_query_space_tree_returns_full_hierarchy(self) -> None:
        """查询空间树返回 Warehouse → Zones → Areas → Locations 完整层级。"""
        tenant_id = uuid4()
        svc, _, _, _, _, _, _ = _new_space_svc()
        perms = frozenset({_WMS_SPACE_MANAGE, _WMS_SPACE_QUERY})

        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            wh = await svc.create_warehouse(
                tenant_id=tenant_id, warehouse_code="WH-TREE", warehouse_name="树仓库"
            )
            zone1 = await svc.create_zone(
                tenant_id=tenant_id,
                warehouse_id=wh.warehouse_id,
                zone_code="Z1",
                zone_name="存储区",
                zone_function="storage",
            )
            zone2 = await svc.create_zone(
                tenant_id=tenant_id,
                warehouse_id=wh.warehouse_id,
                zone_code="Z2",
                zone_name="收货区",
                zone_function="receiving",
            )
            area1 = await svc.create_area(
                tenant_id=tenant_id, zone_id=zone1.zone_id, area_code="A1", area_name="A区"
            )
            loc1 = await svc.create_location(
                tenant_id=tenant_id,
                warehouse_id=wh.warehouse_id,
                zone_id=zone1.zone_id,
                location_code="L1",
                area_id=area1.area_id,
            )
            loc2 = await svc.create_location(
                tenant_id=tenant_id,
                warehouse_id=wh.warehouse_id,
                zone_id=zone1.zone_id,
                location_code="L2",
            )

            tree = await svc.query_space_tree(tenant_id=tenant_id, warehouse_id=wh.warehouse_id)

        # 仓库节点
        assert tree["warehouse_code"] == "WH-TREE"
        assert tree["warehouse_name"] == "树仓库"
        # 两个库区
        assert len(tree["zones"]) == 2
        zone_codes = {z["zone_code"] for z in tree["zones"]}
        assert zone_codes == {"Z1", "Z2"}
        # Z1 含 1 个区域 + 2 个库位
        z1_node = next(z for z in tree["zones"] if z["zone_code"] == "Z1")
        assert len(z1_node["areas"]) == 1
        assert z1_node["areas"][0]["area_code"] == "A1"
        assert len(z1_node["locations"]) == 2
        loc_codes = {l["location_code"] for l in z1_node["locations"]}
        assert loc_codes == {"L1", "L2"}
        # Z2 无区域无库位
        z2_node = next(z for z in tree["zones"] if z["zone_code"] == "Z2")
        assert len(z2_node["areas"]) == 0
        assert len(z2_node["locations"]) == 0

    async def test_query_space_tree_nonexistent_warehouse_rejected(self) -> None:
        """查询不存在的仓库空间树被拒绝。"""
        tenant_id = uuid4()
        svc, _, _, _, _, _, _ = _new_space_svc()
        perms = frozenset({_WMS_SPACE_QUERY})

        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            with pytest.raises(WMSError) as exc:
                await svc.query_space_tree(tenant_id=tenant_id, warehouse_id=uuid4())
        assert exc.value.code == WMSErrorCode.WAREHOUSE_NOT_FOUND

    async def test_toggle_zone_status(self) -> None:
        """切换库区状态：停用后再启用。"""
        tenant_id = uuid4()
        svc, _, _, _, _, _, _ = _new_space_svc()
        perms = frozenset({_WMS_SPACE_MANAGE})

        with _apply_ctx(_make_ctx(tenant_id, permissions=perms)):
            wh = await svc.create_warehouse(
                tenant_id=tenant_id, warehouse_code="WH-T", warehouse_name="仓库"
            )
            zone = await svc.create_zone(
                tenant_id=tenant_id,
                warehouse_id=wh.warehouse_id,
                zone_code="ZT",
                zone_name="切换区",
            )
            assert zone.status == "active"

            disabled = await svc.toggle_zone_status(
                tenant_id=tenant_id, zone_id=zone.zone_id, activate=False
            )
            assert disabled.status == "disabled"

            enabled = await svc.toggle_zone_status(
                tenant_id=tenant_id, zone_id=zone.zone_id, activate=True
            )
            assert enabled.status == "active"