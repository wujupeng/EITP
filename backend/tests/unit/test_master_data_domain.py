"""T08 主数据层级继承单元测试。"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.masterdata.master_data_base import MasterDataBase
from app.domain.masterdata.master_data_events import (
    CompanyOverrideUpdatedEvent,
    MasterDataBaseChangedEvent,
    MasterDataBaseCreatedEvent,
    WarehouseOverrideUpdatedEvent,
)
from app.domain.masterdata.overrides import CompanyOverride, WarehouseOverride
from app.domain.masterdata.permission_guard import MasterDataPermissionGuard
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import DomainError, ErrorCode


class TestMasterDataBase:
    """T08-01: 主数据基准聚合根。"""

    def _make_base(self) -> MasterDataBase:
        return MasterDataBase(
            id=EntityId.generate(),
            enterprise_id=uuid4(),
            sku_code="SKU-001",
            base_attrs={"name": "商品A", "category": "食品", "unit": "个"},
        )

    def test_create_base(self) -> None:
        base = self._make_base()
        assert base.sku_code == "SKU-001"
        assert base.base_attrs["name"] == "商品A"
        assert base.version == 1

    def test_update_base_attrs_increments_version(self) -> None:
        base = self._make_base()
        base.update_base_attrs({"name": "商品A-改"})
        assert base.base_attrs["name"] == "商品A-改"
        assert base.version == 2

    def test_update_base_attrs_optimistic_lock_success(self) -> None:
        base = self._make_base()
        base.update_base_attrs({"name": "改1"}, expected_version=1)
        assert base.version == 2

    def test_update_base_attrs_optimistic_lock_failure(self) -> None:
        base = self._make_base()
        with pytest.raises(DomainError) as exc:
            base.update_base_attrs({"name": "改"}, expected_version=99)
        assert exc.value.code == ErrorCode.MASTER_ATTR_CONFLICT

    def test_update_base_attrs_merges(self) -> None:
        base = self._make_base()
        base.update_base_attrs({"price": 100})
        assert base.base_attrs["name"] == "商品A"
        assert base.base_attrs["price"] == 100

    def test_record_created_event(self) -> None:
        base = self._make_base()
        base.record_created_event()
        events = list(base.pull_events())
        assert any(isinstance(e, MasterDataBaseCreatedEvent) for e in events)

    def test_update_emits_changed_event(self) -> None:
        base = self._make_base()
        base.update_base_attrs({"name": "改"})
        events = list(base.pull_events())
        assert any(isinstance(e, MasterDataBaseChangedEvent) for e in events)


class TestThreeLayerInheritance:
    """T08-02: 三层合并求值。"""

    def _make_base(self) -> MasterDataBase:
        return MasterDataBase(
            id=EntityId.generate(),
            enterprise_id=uuid4(),
            sku_code="SKU-001",
            base_attrs={"name": "商品A", "category": "食品", "unit": "个", "price": 50},
        )

    def test_effective_base_only(self) -> None:
        base = self._make_base()
        effective = base.effective_attrs()
        assert effective["name"] == "商品A"
        assert effective["price"] == 50

    def test_effective_with_company_override(self) -> None:
        base = self._make_base()
        org_id = uuid4()
        override = CompanyOverride.create(
            master_data_id=base.id.value,
            organization_id=org_id,
            company_attrs={"price": 100},
        )
        base.set_company_override(override)

        effective = base.effective_attrs(organization_id=org_id)
        assert effective["price"] == 100
        assert effective["name"] == "商品A"

    def test_effective_with_warehouse_override(self) -> None:
        base = self._make_base()
        org_id = uuid4()
        wh_id = uuid4()

        company = CompanyOverride.create(
            master_data_id=base.id.value,
            organization_id=org_id,
            company_attrs={"price": 100},
        )
        warehouse = WarehouseOverride.create(
            master_data_id=base.id.value,
            warehouse_id=wh_id,
            warehouse_attrs={"safety_stock": 50, "batch_mgmt": True},
        )
        base.set_company_override(company)
        base.set_warehouse_override(warehouse)

        effective = base.effective_attrs(organization_id=org_id, warehouse_id=wh_id)
        assert effective["price"] == 100
        assert effective["safety_stock"] == 50
        assert effective["batch_mgmt"] is True

    def test_warehouse_overrides_company(self) -> None:
        """仓库级覆盖公司级同名键。"""
        base = self._make_base()
        org_id = uuid4()
        wh_id = uuid4()

        company = CompanyOverride.create(
            master_data_id=base.id.value,
            organization_id=org_id,
            company_attrs={"price": 100, "safety_stock": 30},
        )
        warehouse = WarehouseOverride.create(
            master_data_id=base.id.value,
            warehouse_id=wh_id,
            warehouse_attrs={"safety_stock": 50},
        )
        base.set_company_override(company)
        base.set_warehouse_override(warehouse)

        effective = base.effective_attrs(organization_id=org_id, warehouse_id=wh_id)
        assert effective["safety_stock"] == 50
        assert effective["price"] == 100

    def test_company_overrides_base(self) -> None:
        """公司级覆盖集团基准同名键。"""
        base = self._make_base()
        org_id = uuid4()
        override = CompanyOverride.create(
            master_data_id=base.id.value,
            organization_id=org_id,
            company_attrs={"name": "商品A-公司改"},
        )
        base.set_company_override(override)

        effective = base.effective_attrs(organization_id=org_id)
        assert effective["name"] == "商品A-公司改"

    def test_company_override_isolated(self) -> None:
        """公司级属性不影响其他公司。"""
        base = self._make_base()
        org_a = uuid4()
        org_b = uuid4()

        base.set_company_override(
            CompanyOverride.create(base.id.value, org_a, {"price": 100})
        )
        base.set_company_override(
            CompanyOverride.create(base.id.value, org_b, {"price": 105})
        )

        assert base.effective_attrs(organization_id=org_a)["price"] == 100
        assert base.effective_attrs(organization_id=org_b)["price"] == 105
        assert base.effective_attrs()["price"] == 50

    def test_set_company_override_emits_event(self) -> None:
        base = self._make_base()
        override = CompanyOverride.create(base.id.value, uuid4(), {"price": 100})
        base.set_company_override(override)
        events = list(base.pull_events())
        assert any(isinstance(e, CompanyOverrideUpdatedEvent) for e in events)

    def test_set_warehouse_override_emits_event(self) -> None:
        base = self._make_base()
        override = WarehouseOverride.create(base.id.value, uuid4(), {"safety_stock": 50})
        base.set_warehouse_override(override)
        events = list(base.pull_events())
        assert any(isinstance(e, WarehouseOverrideUpdatedEvent) for e in events)

    def test_set_company_override_mismatch_rejected(self) -> None:
        base = self._make_base()
        override = CompanyOverride.create(uuid4(), uuid4(), {"price": 100})
        with pytest.raises(DomainError) as exc:
            base.set_company_override(override)
        assert exc.value.code == ErrorCode.MASTER_ATTR_CONFLICT


class TestCompanyOverride:
    def test_create_override(self) -> None:
        override = CompanyOverride.create(
            master_data_id=uuid4(),
            organization_id=uuid4(),
            company_attrs={"price": 100},
        )
        assert override.company_attrs["price"] == 100
        assert override.version == 0

    def test_update_attrs_merges(self) -> None:
        override = CompanyOverride.create(
            master_data_id=uuid4(),
            organization_id=uuid4(),
            company_attrs={"price": 100, "name": "A"},
        )
        updated = override.update_attrs({"price": 200})
        assert updated.company_attrs["price"] == 200
        assert updated.company_attrs["name"] == "A"
        assert updated.version == 1


class TestWarehouseOverride:
    def test_create_override(self) -> None:
        override = WarehouseOverride.create(
            master_data_id=uuid4(),
            warehouse_id=uuid4(),
            warehouse_attrs={"safety_stock": 50},
        )
        assert override.warehouse_attrs["safety_stock"] == 50

    def test_update_attrs_merges(self) -> None:
        override = WarehouseOverride.create(
            master_data_id=uuid4(),
            warehouse_id=uuid4(),
            warehouse_attrs={"safety_stock": 50, "batch_mgmt": False},
        )
        updated = override.update_attrs({"batch_mgmt": True})
        assert updated.warehouse_attrs["batch_mgmt"] is True
        assert updated.warehouse_attrs["safety_stock"] == 50


class TestPermissionGuard:
    """T08-04: 权限边界守卫。"""

    def test_base_write_group_admin_allowed(self) -> None:
        MasterDataPermissionGuard.enforce_base_write(
            is_group_admin=True,
            enterprise_id=uuid4(),
            master_data_id=uuid4(),
        )

    def test_base_write_subsidiary_admin_rejected(self) -> None:
        with pytest.raises(DomainError) as exc:
            MasterDataPermissionGuard.enforce_base_write(
                is_group_admin=False,
                enterprise_id=uuid4(),
                master_data_id=uuid4(),
            )
        assert exc.value.code == ErrorCode.MASTER_BASE_READONLY

    def test_company_override_same_org_allowed(self) -> None:
        org_id = uuid4()
        MasterDataPermissionGuard.enforce_company_override_write(org_id, org_id)

    def test_company_override_different_org_rejected(self) -> None:
        with pytest.raises(DomainError) as exc:
            MasterDataPermissionGuard.enforce_company_override_write(uuid4(), uuid4())
        assert exc.value.code == ErrorCode.MASTER_ATTR_CONFLICT

    def test_attr_conflict_no_constrained_keys(self) -> None:
        MasterDataPermissionGuard.check_attr_conflict(
            base_attrs={"name": "A"},
            override_attrs={"price": 100},
        )

    def test_attr_conflict_detected(self) -> None:
        with pytest.raises(DomainError) as exc:
            MasterDataPermissionGuard.check_attr_conflict(
                base_attrs={"name": "A"},
                override_attrs={"name": "B", "price": 100},
                constrained_keys={"name"},
            )
        assert exc.value.code == ErrorCode.MASTER_ATTR_CONFLICT

    def test_attr_conflict_no_conflict(self) -> None:
        MasterDataPermissionGuard.check_attr_conflict(
            base_attrs={"name": "A"},
            override_attrs={"price": 100},
            constrained_keys={"name"},
        )