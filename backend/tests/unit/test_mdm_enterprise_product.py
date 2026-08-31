"""EITP-MDM-001-T16-02 企业商品与引用关系聚合根单元测试。

覆盖：
- EnterpriseProductAggregate 引用状态机 active/reference_released/source_disabled
- ProductReferenceAggregate 复合唯一约束（tenant_id + group_product_id）
- ProductCustomizationAggregate 租户级隔离
- EnterpriseCategoryAggregate 树形结构

对应 spec 5.2.1.6 / 5.2.3.5 / 5.2.1.7 / 5.4.1.2，design 2.5。
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.enterprise_product.aggregates.enterprise_category_aggregate import (
    EnterpriseCategoryAggregate,
    EnterpriseCategoryStatus,
    ParentCategoryLevel,
)
from app.domain.enterprise_product.aggregates.enterprise_product_aggregate import (
    EnterpriseProductAggregate,
    ReferenceStatus,
)
from app.domain.enterprise_product.aggregates.product_customization_aggregate import (
    CostModelType,
    InventoryStrategy,
    ProductCustomizationAggregate,
)
from app.domain.enterprise_product.aggregates.product_reference_aggregate import (
    ProductReferenceAggregate,
)
from app.domain.enterprise_product.entities.enterprise_sku import (
    EnterpriseSku,
    EnterpriseSkuStatus,
)
from app.domain.enterprise_product.events.enterprise_product_events import (
    EnterpriseCustomizationPublishedEvent,
    EnterpriseProductReferencedEvent,
    EnterpriseReferenceReleasedEvent,
)
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode


def _make_enterprise_sku(
    tenant_id: uuid4,
    enterprise_product_id: EntityId,
    group_sku_id: uuid4,
    enterprise_sku_code: str = "ES-001",
) -> EnterpriseSku:
    return EnterpriseSku(
        enterprise_sku_id=EntityId.generate(),
        tenant_id=tenant_id,
        enterprise_product_id=enterprise_product_id,
        group_sku_id=group_sku_id,
        enterprise_sku_code=enterprise_sku_code,
        enterprise_sku_name="企业 SKU",
    )


@pytest.fixture
def tenant_id() -> uuid4:
    return uuid4()


@pytest.fixture
def group_product_id() -> uuid4:
    return uuid4()


@pytest.fixture
def enterprise_product(tenant_id: uuid4, group_product_id: uuid4) -> EnterpriseProductAggregate:
    return EnterpriseProductAggregate(
        id=EntityId.generate(),
        tenant_id=tenant_id,
        group_product_id=group_product_id,
        enterprise_product_code="EP-001",
        enterprise_product_name="企业商品 A",
    )


class EnterpriseProductAggregateTest:
    """企业商品聚合根 - 引用状态机 active/reference_released/source_disabled。"""

    def test_create_with_valid_parameters(
        self, tenant_id: uuid4, group_product_id: uuid4
    ) -> None:
        eid = EntityId.generate()
        product = EnterpriseProductAggregate(
            id=eid,
            tenant_id=tenant_id,
            group_product_id=group_product_id,
            enterprise_product_code="EP-100",
            enterprise_product_name="企业商品",
        )
        assert product.id == eid
        assert product.tenant_id == tenant_id
        assert product.group_product_id == group_product_id
        assert product.enterprise_product_code == "EP-100"
        assert product.reference_status == ReferenceStatus.ACTIVE
        assert product.is_active() is True
        assert product.enterprise_skus == []
        assert product.published_version == 0

    def test_disable_transitions_active_to_reference_released(
        self, enterprise_product: EnterpriseProductAggregate
    ) -> None:
        assert enterprise_product.reference_status == ReferenceStatus.ACTIVE
        enterprise_product.disable()
        assert enterprise_product.reference_status == ReferenceStatus.REFERENCE_RELEASED
        assert enterprise_product.is_active() is False

    def test_disable_idempotent_when_already_released(
        self, enterprise_product: EnterpriseProductAggregate
    ) -> None:
        enterprise_product.disable()
        enterprise_product.disable()
        assert enterprise_product.reference_status == ReferenceStatus.REFERENCE_RELEASED

    def test_disable_with_active_documents_rejected(
        self, enterprise_product: EnterpriseProductAggregate
    ) -> None:
        enterprise_product.mark_has_active_documents()
        with pytest.raises(MDMError) as exc:
            enterprise_product.disable()
        assert exc.value.code == MDMErrorCode.REFERENCE_HAS_ACTIVE_DOCUMENT
        assert enterprise_product.reference_status == ReferenceStatus.ACTIVE

    def test_mark_source_disabled_transitions_to_source_disabled(
        self, enterprise_product: EnterpriseProductAggregate
    ) -> None:
        enterprise_product.mark_source_disabled()
        assert enterprise_product.reference_status == ReferenceStatus.SOURCE_DISABLED
        assert enterprise_product.is_active() is False

    def test_mark_source_disabled_idempotent(
        self, enterprise_product: EnterpriseProductAggregate
    ) -> None:
        enterprise_product.mark_source_disabled()
        enterprise_product.mark_source_disabled()
        assert enterprise_product.reference_status == ReferenceStatus.SOURCE_DISABLED

    def test_release_reference_transitions_to_released(
        self, enterprise_product: EnterpriseProductAggregate
    ) -> None:
        released_by = uuid4()
        enterprise_product.release_reference(released_by)
        assert enterprise_product.reference_status == ReferenceStatus.REFERENCE_RELEASED
        events = list(enterprise_product.pull_events())
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, EnterpriseReferenceReleasedEvent)
        assert event.tenant_id == enterprise_product.tenant_id
        assert event.enterprise_product_id == enterprise_product.id.value
        assert event.group_product_id == enterprise_product.group_product_id
        assert event.released_by == released_by

    def test_release_reference_with_active_documents_rejected(
        self, enterprise_product: EnterpriseProductAggregate
    ) -> None:
        enterprise_product.mark_has_active_documents()
        with pytest.raises(MDMError) as exc:
            enterprise_product.release_reference(uuid4())
        assert exc.value.code == MDMErrorCode.REFERENCE_HAS_ACTIVE_DOCUMENT
        assert enterprise_product.reference_status == ReferenceStatus.ACTIVE

    def test_release_reference_idempotent_when_already_released(
        self, enterprise_product: EnterpriseProductAggregate
    ) -> None:
        enterprise_product.release_reference(uuid4())
        enterprise_product.clear_events()
        enterprise_product.release_reference(uuid4())
        assert enterprise_product.reference_status == ReferenceStatus.REFERENCE_RELEASED
        assert list(enterprise_product.pull_events()) == []

    def test_create_reference_records_event(
        self, tenant_id: uuid4, group_product_id: uuid4
    ) -> None:
        referenced_by = uuid4()
        product = EnterpriseProductAggregate.create_reference(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            group_product_id=group_product_id,
            enterprise_product_code="EP-REF",
            referenced_by=referenced_by,
        )
        assert product.reference_status == ReferenceStatus.ACTIVE
        assert product.referenced_by == referenced_by
        events = list(product.pull_events())
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, EnterpriseProductReferencedEvent)
        assert event.tenant_id == tenant_id
        assert event.group_product_id == group_product_id
        assert event.referenced_by == referenced_by

    def test_resolve_product_name_inherits_group_when_empty(
        self, tenant_id: uuid4, group_product_id: uuid4
    ) -> None:
        product = EnterpriseProductAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            group_product_id=group_product_id,
            enterprise_product_code="EP-N",
            enterprise_product_name=None,
        )
        assert product.resolve_product_name("集团商品名") == "集团商品名"
        product.update_name("企业自定义名")
        assert product.resolve_product_name("集团商品名") == "企业自定义名"

    def test_add_enterprise_sku_appends_sku(
        self, enterprise_product: EnterpriseProductAggregate, tenant_id: uuid4
    ) -> None:
        sku = _make_enterprise_sku(tenant_id, enterprise_product.id, uuid4(), "ES-A")
        enterprise_product.add_enterprise_sku(sku)
        assert len(enterprise_product.enterprise_skus) == 1
        assert enterprise_product.enterprise_skus[0].enterprise_sku_code == "ES-A"

    def test_add_enterprise_sku_cross_tenant_rejected(
        self, enterprise_product: EnterpriseProductAggregate
    ) -> None:
        other_tenant = uuid4()
        sku = _make_enterprise_sku(other_tenant, enterprise_product.id, uuid4(), "ES-X")
        with pytest.raises(MDMError) as exc:
            enterprise_product.add_enterprise_sku(sku)
        assert exc.value.code == MDMErrorCode.CROSS_TENANT_POLICY_DENIED
        assert enterprise_product.enterprise_skus == []

    def test_add_enterprise_sku_mismatched_product_rejected(
        self, enterprise_product: EnterpriseProductAggregate, tenant_id: uuid4
    ) -> None:
        other_product_id = EntityId.generate()
        sku = _make_enterprise_sku(tenant_id, other_product_id, uuid4(), "ES-Y")
        with pytest.raises(MDMError) as exc:
            enterprise_product.add_enterprise_sku(sku)
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_get_enterprise_sku_returns_matching(
        self, enterprise_product: EnterpriseProductAggregate, tenant_id: uuid4
    ) -> None:
        sku = _make_enterprise_sku(tenant_id, enterprise_product.id, uuid4(), "ES-G")
        enterprise_product.add_enterprise_sku(sku)
        found = enterprise_product.get_enterprise_sku(sku.enterprise_sku_id)
        assert found is not None
        assert found.enterprise_sku_id == sku.enterprise_sku_id

    def test_get_enterprise_sku_returns_none_when_missing(
        self, enterprise_product: EnterpriseProductAggregate
    ) -> None:
        assert enterprise_product.get_enterprise_sku(EntityId.generate()) is None

    def test_update_category(self, enterprise_product: EnterpriseProductAggregate) -> None:
        new_category = uuid4()
        enterprise_product.update_category(new_category)
        assert enterprise_product.enterprise_category_id == new_category

    def test_update_category_to_none(self, enterprise_product: EnterpriseProductAggregate) -> None:
        enterprise_product.update_category(None)
        assert enterprise_product.enterprise_category_id is None

    def test_properties_access(
        self, tenant_id: uuid4, group_product_id: uuid4
    ) -> None:
        category_id = uuid4()
        product = EnterpriseProductAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            group_product_id=group_product_id,
            enterprise_product_code="EP-PA",
            enterprise_product_name="属性访问",
            enterprise_category_id=category_id,
        )
        assert product.enterprise_product_name == "属性访问"
        assert product.enterprise_category_id == category_id
        assert product.referenced_by is None


class EnterpriseSkuTest:
    """企业 SKU 实体 - 继承集团 SKU 编码与条码补充。"""

    def test_resolve_sku_code_inherits_group_when_empty(self) -> None:
        sku = _make_enterprise_sku(uuid4(), EntityId.generate(), uuid4(), "ES-C")
        assert sku.resolve_sku_code("GS-CODE") == "ES-C"
        empty_sku = EnterpriseSku(
            enterprise_sku_id=EntityId.generate(),
            tenant_id=uuid4(),
            enterprise_product_id=EntityId.generate(),
            group_sku_id=uuid4(),
        )
        assert empty_sku.resolve_sku_code("GS-CODE") == "GS-CODE"

    def test_resolve_sku_name_inherits_group_when_empty(self) -> None:
        sku = EnterpriseSku(
            enterprise_sku_id=EntityId.generate(),
            tenant_id=uuid4(),
            enterprise_product_id=EntityId.generate(),
            group_sku_id=uuid4(),
            enterprise_sku_name="企业名",
        )
        assert sku.resolve_sku_name("集团名") == "企业名"
        empty_sku = EnterpriseSku(
            enterprise_sku_id=EntityId.generate(),
            tenant_id=uuid4(),
            enterprise_product_id=EntityId.generate(),
            group_sku_id=uuid4(),
        )
        assert empty_sku.resolve_sku_name("集团名") == "集团名"

    def test_add_barcode_appends_unique(self) -> None:
        sku = EnterpriseSku(
            enterprise_sku_id=EntityId.generate(),
            tenant_id=uuid4(),
            enterprise_product_id=EntityId.generate(),
            group_sku_id=uuid4(),
            enterprise_barcode_list=["EBC-1"],
        )
        sku.add_barcode("EBC-2")
        assert sku.enterprise_barcode_list == ["EBC-1", "EBC-2"]
        sku.add_barcode("EBC-1")
        assert sku.enterprise_barcode_list == ["EBC-1", "EBC-2"]

    def test_state_machine_disable_enable(self) -> None:
        sku = _make_enterprise_sku(uuid4(), EntityId.generate(), uuid4())
        assert sku.status == EnterpriseSkuStatus.ACTIVE
        sku.disable()
        assert sku.status == EnterpriseSkuStatus.DISABLED
        assert sku.is_active() is False
        sku.enable()
        assert sku.status == EnterpriseSkuStatus.ACTIVE


class ProductReferenceAggregateTest:
    """商品引用关系聚合根 - 复合唯一约束（tenant_id + group_product_id）。"""

    def test_create_reference_with_valid_parameters(
        self, tenant_id: uuid4, group_product_id: uuid4
    ) -> None:
        ref = ProductReferenceAggregate.create(
            tenant_id=tenant_id,
            group_product_id=group_product_id,
            enterprise_product_id=uuid4(),
            referenced_by=uuid4(),
        )
        assert ref.tenant_id == tenant_id
        assert ref.group_product_id == group_product_id
        assert ref.reference_status == ReferenceStatus.ACTIVE
        assert ref.is_active() is True
        assert ref.released_by is None
        assert ref.released_at is None

    def test_validate_no_duplicate_rejects_same_tenant_and_group(
        self, tenant_id: uuid4, group_product_id: uuid4
    ) -> None:
        existing = [(tenant_id, group_product_id)]
        with pytest.raises(MDMError) as exc:
            ProductReferenceAggregate.validate_no_duplicate(
                existing_refs=existing,
                tenant_id=tenant_id,
                group_product_id=group_product_id,
            )
        assert exc.value.code == MDMErrorCode.DUPLICATE_REFERENCE

    def test_validate_no_duplicate_allows_different_tenant(
        self, tenant_id: uuid4, group_product_id: uuid4
    ) -> None:
        other_tenant = uuid4()
        existing = [(other_tenant, group_product_id)]
        ProductReferenceAggregate.validate_no_duplicate(
            existing_refs=existing,
            tenant_id=tenant_id,
            group_product_id=group_product_id,
        )

    def test_validate_no_duplicate_allows_different_group(
        self, tenant_id: uuid4, group_product_id: uuid4
    ) -> None:
        other_group = uuid4()
        existing = [(tenant_id, other_group)]
        ProductReferenceAggregate.validate_no_duplicate(
            existing_refs=existing,
            tenant_id=tenant_id,
            group_product_id=group_product_id,
        )

    def test_validate_no_duplicate_passes_on_empty_list(
        self, tenant_id: uuid4, group_product_id: uuid4
    ) -> None:
        ProductReferenceAggregate.validate_no_duplicate(
            existing_refs=[],
            tenant_id=tenant_id,
            group_product_id=group_product_id,
        )

    def test_release_transitions_to_released(
        self, tenant_id: uuid4, group_product_id: uuid4
    ) -> None:
        ref = ProductReferenceAggregate.create(
            tenant_id=tenant_id,
            group_product_id=group_product_id,
            enterprise_product_id=uuid4(),
            referenced_by=uuid4(),
        )
        released_by = uuid4()
        ref.release(released_by)
        assert ref.reference_status == ReferenceStatus.REFERENCE_RELEASED
        assert ref.released_by == released_by
        assert ref.released_at is not None
        assert ref.is_active() is False

    def test_release_idempotent_when_already_released(
        self, tenant_id: uuid4, group_product_id: uuid4
    ) -> None:
        ref = ProductReferenceAggregate.create(
            tenant_id=tenant_id,
            group_product_id=group_product_id,
            enterprise_product_id=uuid4(),
            referenced_by=uuid4(),
        )
        ref.release(uuid4())
        first_released_at = ref.released_at
        ref.release(uuid4())
        assert ref.reference_status == ReferenceStatus.REFERENCE_RELEASED
        assert ref.released_at == first_released_at

    def test_mark_source_disabled_transitions_to_source_disabled(
        self, tenant_id: uuid4, group_product_id: uuid4
    ) -> None:
        ref = ProductReferenceAggregate.create(
            tenant_id=tenant_id,
            group_product_id=group_product_id,
            enterprise_product_id=uuid4(),
            referenced_by=uuid4(),
        )
        ref.mark_source_disabled()
        assert ref.reference_status == ReferenceStatus.SOURCE_DISABLED
        assert ref.is_active() is False

    def test_mark_source_disabled_idempotent(
        self, tenant_id: uuid4, group_product_id: uuid4
    ) -> None:
        ref = ProductReferenceAggregate.create(
            tenant_id=tenant_id,
            group_product_id=group_product_id,
            enterprise_product_id=uuid4(),
            referenced_by=uuid4(),
        )
        ref.mark_source_disabled()
        ref.mark_source_disabled()
        assert ref.reference_status == ReferenceStatus.SOURCE_DISABLED


class ProductCustomizationAggregateTest:
    """商品定制聚合根 - 租户级隔离与企业级属性覆盖。"""

    def _make_customization(
        self, tenant_id: uuid4, enterprise_product_id: uuid4
    ) -> ProductCustomizationAggregate:
        return ProductCustomizationAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            enterprise_product_id=enterprise_product_id,
        )

    def test_create_with_tenant_isolation(
        self, tenant_id: uuid4
    ) -> None:
        cust = self._make_customization(tenant_id, uuid4())
        assert cust.tenant_id == tenant_id
        assert cust.version == 0
        assert cust.custom_attributes == {}
        assert cust.sales_price is None
        assert cust.purchase_price is None
        assert cust.inventory_strategy is None
        assert cust.safety_stock is None
        assert cust.cost_model is None

    def test_update_sales_price(self, tenant_id: uuid4) -> None:
        cust = self._make_customization(tenant_id, uuid4())
        cust.update_sales_price(Decimal("99.50"))
        assert cust.sales_price == Decimal("99.50")

    def test_update_sales_price_negative_rejected(self, tenant_id: uuid4) -> None:
        cust = self._make_customization(tenant_id, uuid4())
        with pytest.raises(MDMError) as exc:
            cust.update_sales_price(Decimal("-1"))
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID
        assert cust.sales_price is None

    def test_update_purchase_price(self, tenant_id: uuid4) -> None:
        cust = self._make_customization(tenant_id, uuid4())
        cust.update_purchase_price(Decimal("50.00"))
        assert cust.purchase_price == Decimal("50.00")

    def test_update_purchase_price_negative_rejected(self, tenant_id: uuid4) -> None:
        cust = self._make_customization(tenant_id, uuid4())
        with pytest.raises(MDMError) as exc:
            cust.update_purchase_price(Decimal("-0.01"))
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_update_inventory_strategy(self, tenant_id: uuid4) -> None:
        cust = self._make_customization(tenant_id, uuid4())
        cust.update_inventory_strategy(InventoryStrategy.WARNING)
        assert cust.inventory_strategy == InventoryStrategy.WARNING

    def test_update_safety_stock(self, tenant_id: uuid4) -> None:
        cust = self._make_customization(tenant_id, uuid4())
        cust.update_safety_stock(Decimal("100"))
        assert cust.safety_stock == Decimal("100")

    def test_update_safety_stock_negative_rejected(self, tenant_id: uuid4) -> None:
        cust = self._make_customization(tenant_id, uuid4())
        with pytest.raises(MDMError) as exc:
            cust.update_safety_stock(Decimal("-1"))
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_update_cost_model(self, tenant_id: uuid4) -> None:
        cust = self._make_customization(tenant_id, uuid4())
        cust.update_cost_model(CostModelType.FIFO)
        assert cust.cost_model == CostModelType.FIFO

    def test_update_custom_attributes(self, tenant_id: uuid4) -> None:
        cust = self._make_customization(tenant_id, uuid4())
        cust.update_custom_attributes({"label": "定制标签", "priority": 5})
        assert cust.custom_attributes == {"label": "定制标签", "priority": 5}

    def test_publish_increases_version_and_records_event(self, tenant_id: uuid4) -> None:
        cust = self._make_customization(tenant_id, uuid4())
        cust.publish(new_version=1)
        assert cust.version == 1
        events = list(cust.pull_events())
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, EnterpriseCustomizationPublishedEvent)
        assert event.tenant_id == tenant_id
        assert event.version == 1

    def test_publish_rejects_non_increasing_version(self, tenant_id: uuid4) -> None:
        cust = self._make_customization(tenant_id, uuid4())
        cust.publish(new_version=2)
        with pytest.raises(MDMError) as exc:
            cust.publish(new_version=2)
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID
        assert cust.version == 2

    def test_tenant_isolation_different_tenants_independent(self) -> None:
        tenant_a = uuid4()
        tenant_b = uuid4()
        cust_a = self._make_customization(tenant_a, uuid4())
        cust_b = self._make_customization(tenant_b, uuid4())
        cust_a.update_sales_price(Decimal("10"))
        cust_b.update_sales_price(Decimal("20"))
        assert cust_a.tenant_id != cust_b.tenant_id
        assert cust_a.sales_price != cust_b.sales_price
        assert cust_a.sales_price == Decimal("10")
        assert cust_b.sales_price == Decimal("20")


class EnterpriseCategoryAggregateTest:
    """企业分类聚合根 - 树形结构与租户级隔离。"""

    def _make_category(
        self,
        tenant_id: uuid4,
        code: str = "ECAT-ROOT",
        parent_category_id: uuid4 | None = None,
        parent_category_level: ParentCategoryLevel | None = None,
        level: int = 1,
    ) -> EnterpriseCategoryAggregate:
        return EnterpriseCategoryAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            enterprise_category_code=code,
            enterprise_category_name=code,
            level=level,
            parent_category_id=parent_category_id,
            parent_category_level=parent_category_level,
        )

    def test_create_root_category(self, tenant_id: uuid4) -> None:
        cat = self._make_category(tenant_id, "ECAT-R")
        assert cat.tenant_id == tenant_id
        assert cat.parent_category_id is None
        assert cat.level == 1
        assert cat.is_active() is True
        assert cat.children == []

    def test_add_child_sets_level_and_enterprise_parent(self, tenant_id: uuid4) -> None:
        parent = self._make_category(tenant_id, "ECAT-P")
        child = EnterpriseCategoryAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            enterprise_category_code="ECAT-C",
            enterprise_category_name="子",
            parent_category_id=parent.id.value,
        )
        parent.add_child(child)
        assert len(parent.children) == 1
        assert parent.children[0].level == parent.level + 1
        assert parent.children[0].parent_category_level == ParentCategoryLevel.ENTERPRISE

    def test_add_child_cross_tenant_rejected(self, tenant_id: uuid4) -> None:
        parent = self._make_category(tenant_id, "ECAT-P")
        other_tenant = uuid4()
        child = EnterpriseCategoryAggregate(
            id=EntityId.generate(),
            tenant_id=other_tenant,
            enterprise_category_code="ECAT-C",
            enterprise_category_name="跨租户子",
            parent_category_id=parent.id.value,
        )
        with pytest.raises(MDMError) as exc:
            parent.add_child(child)
        assert exc.value.code == MDMErrorCode.CROSS_TENANT_POLICY_DENIED

    def test_add_child_mismatched_parent_rejected(self, tenant_id: uuid4) -> None:
        parent = self._make_category(tenant_id, "ECAT-P")
        child = EnterpriseCategoryAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            enterprise_category_code="ECAT-C",
            enterprise_category_name="子",
            parent_category_id=uuid4(),
        )
        with pytest.raises(MDMError) as exc:
            parent.add_child(child)
        assert exc.value.code == MDMErrorCode.CATEGORY_MULTI_BELONG_DENIED

    def test_validate_no_cycle_passes_on_tree(self, tenant_id: uuid4) -> None:
        root = self._make_category(tenant_id, "ECAT-R")
        child = EnterpriseCategoryAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            enterprise_category_code="ECAT-C1",
            enterprise_category_name="子1",
            parent_category_id=root.id.value,
        )
        root.add_child(child)
        root.validate_no_cycle()

    def test_validate_no_cycle_detects_cycle(self, tenant_id: uuid4) -> None:
        root = self._make_category(tenant_id, "ECAT-R")
        child = EnterpriseCategoryAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            enterprise_category_code="ECAT-C",
            enterprise_category_name="子",
            parent_category_id=root.id.value,
        )
        root.add_child(child)
        with pytest.raises(MDMError) as exc:
            root.validate_no_cycle(visited={root.id.value, child.id.value})
        assert exc.value.code == MDMErrorCode.CATEGORY_CYCLE

    def test_disable_enable_state_machine(self, tenant_id: uuid4) -> None:
        cat = self._make_category(tenant_id, "ECAT-S")
        cat.disable()
        assert cat.status == EnterpriseCategoryStatus.DISABLED
        assert cat.is_active() is False
        cat.enable()
        assert cat.status == EnterpriseCategoryStatus.ACTIVE
        assert cat.is_active() is True

    def test_disable_idempotent(self, tenant_id: uuid4) -> None:
        cat = self._make_category(tenant_id, "ECAT-S")
        cat.disable()
        cat.disable()
        assert cat.status == EnterpriseCategoryStatus.DISABLED

    def test_update_name(self, tenant_id: uuid4) -> None:
        cat = self._make_category(tenant_id, "ECAT-N")
        cat.update_name("新企业分类名")
        assert cat.enterprise_category_name == "新企业分类名"