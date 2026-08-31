"""EITP-INV-001 商品聚合根、分类聚合根、单位换算值对象单元测试。"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.inventory.events.inventory_events import ProductStatusChangedEvent
from app.domain.inventory.value_objects.shared import ProductStatus
from app.domain.product.aggregates.category_aggregate import CategoryAggregate
from app.domain.product.aggregates.product_aggregate import ProductAggregate, Sku
from app.domain.product.value_objects.unit_conversion import UnitConversion
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import INVError, INVErrorCode


def _make_sku(
    tenant_id: uuid4 | None = None,
    product_id: EntityId | None = None,
    sku_code: str = "SKU-001",
) -> Sku:
    return Sku(
        sku_id=EntityId.generate(),
        tenant_id=tenant_id or uuid4(),
        product_id=product_id or EntityId.generate(),
        sku_code=sku_code,
        sku_name="测试 SKU",
        unit_id=uuid4(),
    )


@pytest.fixture
def tenant_id() -> uuid4:
    return uuid4()


@pytest.fixture
def product(tenant_id: uuid4) -> ProductAggregate:
    return ProductAggregate(
        id=EntityId.generate(),
        tenant_id=tenant_id,
        product_code="P-001",
        product_name="测试商品",
        category_id=uuid4(),
        brand_id=uuid4(),
        base_unit_id=uuid4(),
        description="描述",
    )


class ProductAggregateTest:
    def test_create_with_valid_parameters(self, tenant_id: uuid4) -> None:
        category_id = uuid4()
        brand_id = uuid4()
        base_unit_id = uuid4()
        pid = EntityId.generate()
        product = ProductAggregate(
            id=pid,
            tenant_id=tenant_id,
            product_code="P-100",
            product_name="商品 A",
            category_id=category_id,
            brand_id=brand_id,
            base_unit_id=base_unit_id,
            description="商品 A 描述",
        )
        assert product.id == pid
        assert product.tenant_id == tenant_id
        assert product.product_code == "P-100"
        assert product.product_name == "商品 A"
        assert product.category_id == category_id
        assert product.brand_id == brand_id
        assert product.base_unit_id == base_unit_id
        assert product.status == ProductStatus.ACTIVE
        assert product.is_active() is True
        assert product.skus == []
        assert product.has_active_documents() is False

    def test_add_sku_appends_sku(self, product: ProductAggregate, tenant_id: uuid4) -> None:
        sku = _make_sku(tenant_id=tenant_id, product_id=product.id, sku_code="SKU-A")
        product.add_sku(sku)
        assert len(product.skus) == 1
        assert product.skus[0].sku_code == "SKU-A"

    def test_add_sku_duplicate_code_rejected(
        self, product: ProductAggregate, tenant_id: uuid4
    ) -> None:
        sku1 = _make_sku(tenant_id=tenant_id, product_id=product.id, sku_code="SKU-DUP")
        product.add_sku(sku1)
        sku2 = _make_sku(tenant_id=tenant_id, product_id=product.id, sku_code="SKU-DUP")
        with pytest.raises(INVError) as exc:
            product.add_sku(sku2)
        assert exc.value.code == INVErrorCode.SKU_DUPLICATE
        assert len(product.skus) == 1

    def test_add_sku_cross_tenant_rejected(
        self, product: ProductAggregate, tenant_id: uuid4
    ) -> None:
        other_tenant = uuid4()
        sku = _make_sku(tenant_id=other_tenant, product_id=product.id, sku_code="SKU-X")
        with pytest.raises(INVError) as exc:
            product.add_sku(sku)
        assert exc.value.code == INVErrorCode.CROSS_TENANT_REF_DENIED
        assert product.skus == []

    def test_disable_with_active_documents_rejected(self, product: ProductAggregate) -> None:
        product.mark_has_active_documents()
        with pytest.raises(INVError) as exc:
            product.disable()
        assert exc.value.code == INVErrorCode.PRODUCT_HAS_ACTIVE_DOCUMENT
        assert product.status == ProductStatus.ACTIVE

    def test_disable_with_force_bypasses_active_documents(self, product: ProductAggregate) -> None:
        product.mark_has_active_documents()
        product.disable(force=True)
        assert product.status == ProductStatus.DISABLED
        assert product.is_active() is False

    def test_disable_idempotent_when_already_disabled(self, product: ProductAggregate) -> None:
        product.disable()
        product.disable()
        assert product.status == ProductStatus.DISABLED

    def test_enable_from_disabled_state(self, product: ProductAggregate) -> None:
        product.disable()
        assert product.status == ProductStatus.DISABLED
        product.enable()
        assert product.status == ProductStatus.ACTIVE
        assert product.is_active() is True

    def test_enable_idempotent_when_already_active(self, product: ProductAggregate) -> None:
        product.enable()
        assert product.status == ProductStatus.ACTIVE

    def test_disable_records_status_changed_event(self, product: ProductAggregate) -> None:
        product.disable()
        events = list(product.pull_events())
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, ProductStatusChangedEvent)
        assert event.from_status == ProductStatus.ACTIVE.value
        assert event.to_status == ProductStatus.DISABLED.value
        assert event.product_id == product.id.value
        assert event.event_type == "ProductStatusChangedEvent"
        assert event.tenant_id == product.tenant_id

    def test_enable_records_status_changed_event(self, product: ProductAggregate) -> None:
        product.disable()
        product.clear_events()
        product.enable()
        events = list(product.pull_events())
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, ProductStatusChangedEvent)
        assert event.from_status == ProductStatus.DISABLED.value
        assert event.to_status == ProductStatus.ACTIVE.value

    def test_get_sku_returns_matching_sku(
        self, product: ProductAggregate, tenant_id: uuid4
    ) -> None:
        sku = _make_sku(tenant_id=tenant_id, product_id=product.id, sku_code="SKU-G")
        product.add_sku(sku)
        found = product.get_sku(sku.sku_id)
        assert found is not None
        assert found.sku_id == sku.sku_id

    def test_get_sku_returns_none_when_missing(self, product: ProductAggregate) -> None:
        assert product.get_sku(EntityId.generate()) is None

    def test_update_name_and_description(self, product: ProductAggregate) -> None:
        product.update_name("新名称")
        product.update_description("新描述")
        assert product.product_name == "新名称"
        assert product.description == "新描述"


class CategoryAggregateTest:
    def test_create_root_category(self, tenant_id: uuid4) -> None:
        category = CategoryAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            category_code="CAT-ROOT",
            category_name="根分类",
        )
        assert category.parent_category_id is None
        assert category.is_root() is True
        assert category.level == 1
        assert category.is_active() is True

    def test_create_child_category(self, tenant_id: uuid4) -> None:
        parent_id = uuid4()
        category = CategoryAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            category_code="CAT-CHILD",
            category_name="子分类",
            parent_category_id=parent_id,
            level=2,
        )
        assert category.parent_category_id == parent_id
        assert category.is_root() is False
        assert category.level == 2

    def test_validate_no_cycle_detects_self_in_ancestors(self, tenant_id: uuid4) -> None:
        cid = EntityId.generate()
        category = CategoryAggregate(
            id=cid,
            tenant_id=tenant_id,
            category_code="CAT-CYCLE",
            category_name="循环分类",
            parent_category_id=uuid4(),
        )
        with pytest.raises(INVError) as exc:
            category.validate_no_cycle([cid.value])
        assert exc.value.code == INVErrorCode.CATEGORY_DUPLICATE

    def test_validate_no_cycle_passes_when_self_not_in_ancestors(
        self, tenant_id: uuid4
    ) -> None:
        category = CategoryAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            category_code="CAT-OK",
            category_name="正常分类",
            parent_category_id=uuid4(),
        )
        category.validate_no_cycle([uuid4(), uuid4()])

    def test_properties_access(self, tenant_id: uuid4) -> None:
        parent_id = uuid4()
        category = CategoryAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            category_code="CAT-P",
            category_name="属性分类",
            parent_category_id=parent_id,
            level=3,
        )
        assert category.tenant_id == tenant_id
        assert category.category_code == "CAT-P"
        assert category.category_name == "属性分类"
        assert category.level == 3
        assert category.status == ProductStatus.ACTIVE
        assert category.is_active() is True


class SkuTest:
    def test_sku_properties_access(self) -> None:
        sku_id = EntityId.generate()
        tenant_id = uuid4()
        product_id = EntityId.generate()
        unit_id = uuid4()
        sku = Sku(
            sku_id=sku_id,
            tenant_id=tenant_id,
            product_id=product_id,
            sku_code="SKU-P1",
            sku_name="规格 A",
            unit_id=unit_id,
            specification={"color": "red"},
            barcode_list=["BC-001", "BC-002"],
            weight=1.5,
            volume=0.2,
        )
        assert sku.sku_id == sku_id
        assert sku.tenant_id == tenant_id
        assert sku.product_id == product_id
        assert sku.sku_code == "SKU-P1"
        assert sku.sku_name == "规格 A"
        assert sku.unit_id == unit_id
        assert sku.specification == {"color": "red"}
        assert sku.barcode_list == ["BC-001", "BC-002"]
        assert sku.weight == 1.5
        assert sku.volume == 0.2
        assert sku.status == ProductStatus.ACTIVE
        assert sku.is_active() is True

    def test_sku_defaults_empty_collections(self) -> None:
        sku = Sku(
            sku_id=EntityId.generate(),
            tenant_id=uuid4(),
            product_id=EntityId.generate(),
            sku_code="SKU-D",
            sku_name="默认",
            unit_id=uuid4(),
        )
        assert sku.specification == {}
        assert sku.barcode_list == []
        assert sku.weight is None
        assert sku.volume is None


class UnitConversionTest:
    def test_create_valid_conversion(self) -> None:
        from_unit = uuid4()
        to_unit = uuid4()
        conv = UnitConversion(from_unit_id=from_unit, to_unit_id=to_unit, ratio=12.0)
        assert conv.from_unit_id == from_unit
        assert conv.to_unit_id == to_unit
        assert conv.ratio == 12.0

    def test_zero_ratio_rejected(self) -> None:
        with pytest.raises(ValueError):
            UnitConversion(from_unit_id=uuid4(), to_unit_id=uuid4(), ratio=0.0)

    def test_negative_ratio_rejected(self) -> None:
        with pytest.raises(ValueError):
            UnitConversion(from_unit_id=uuid4(), to_unit_id=uuid4(), ratio=-1.5)

    def test_self_unit_rejected(self) -> None:
        unit = uuid4()
        with pytest.raises(ValueError):
            UnitConversion(from_unit_id=unit, to_unit_id=unit, ratio=1.0)

    def test_inverse(self) -> None:
        from_unit = uuid4()
        to_unit = uuid4()
        conv = UnitConversion(from_unit_id=from_unit, to_unit_id=to_unit, ratio=10.0)
        inv = conv.inverse()
        assert inv.from_unit_id == to_unit
        assert inv.to_unit_id == from_unit
        assert inv.ratio == pytest.approx(0.1)

    def test_compose_continuous_chain(self) -> None:
        unit_a = uuid4()
        unit_b = uuid4()
        unit_c = uuid4()
        ab = UnitConversion(from_unit_id=unit_a, to_unit_id=unit_b, ratio=10.0)
        bc = UnitConversion(from_unit_id=unit_b, to_unit_id=unit_c, ratio=100.0)
        ac = ab.compose(bc)
        assert ac.from_unit_id == unit_a
        assert ac.to_unit_id == unit_c
        assert ac.ratio == pytest.approx(1000.0)

    def test_compose_discontinuous_chain_rejected(self) -> None:
        ab = UnitConversion(from_unit_id=uuid4(), to_unit_id=uuid4(), ratio=10.0)
        cd = UnitConversion(from_unit_id=uuid4(), to_unit_id=uuid4(), ratio=100.0)
        with pytest.raises(ValueError):
            ab.compose(cd)