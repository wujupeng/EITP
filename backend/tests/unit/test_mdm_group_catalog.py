"""EITP-MDM-001-T16-01 集团商品目录聚合根单元测试。

覆盖：
- GroupProductAggregate 状态机 active↔disabled、停用校验活跃引用、集团 SKU 全平台编码唯一
- GroupCategoryAggregate 树形结构禁止循环引用
- GroupUnitConversion 换算率循环/矛盾被拒绝

对应 spec 5.1.1.3 / 5.1.1.7 / 5.4.1.3 / 5.5.1.3，design 2.1 / 2.4。
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.group_catalog.aggregates.group_category_aggregate import (
    CategoryStatus,
    GroupCategoryAggregate,
)
from app.domain.group_catalog.aggregates.group_product_aggregate import (
    GroupProductAggregate,
    GroupProductStatus,
)
from app.domain.group_catalog.entities.group_sku import GroupSku, GroupSkuStatus
from app.domain.group_catalog.events.group_catalog_events import (
    GroupProductDisabledEvent,
    GroupProductPublishedEvent,
    GroupSkuCreatedEvent,
)
from app.domain.group_catalog.value_objects.group_unit_conversion import (
    GroupUnitConversion,
)
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode


def _make_group_sku(
    group_product_id: EntityId,
    group_sku_code: str = "GS-001",
    barcode_list: list[str] | None = None,
) -> GroupSku:
    return GroupSku(
        group_sku_id=EntityId.generate(),
        group_product_id=group_product_id,
        group_sku_code=group_sku_code,
        group_sku_name="集团 SKU",
        unit_id=uuid4(),
        barcode_list=barcode_list or [],
    )


@pytest.fixture
def group_product() -> GroupProductAggregate:
    return GroupProductAggregate(
        id=EntityId.generate(),
        group_product_code="GP-001",
        group_product_name="集团商品 A",
        base_unit_id=uuid4(),
        group_category_id=uuid4(),
        group_brand_id=uuid4(),
        description="集团商品描述",
    )


class GroupProductAggregateTest:
    """集团商品聚合根 - 状态机与集团 SKU 唯一编码。"""

    def test_create_with_valid_parameters(self) -> None:
        pid = EntityId.generate()
        unit_id = uuid4()
        product = GroupProductAggregate(
            id=pid,
            group_product_code="GP-100",
            group_product_name="商品 A",
            base_unit_id=unit_id,
        )
        assert product.id == pid
        assert product.group_product_code == "GP-100"
        assert product.group_product_name == "商品 A"
        assert product.base_unit_id == unit_id
        assert product.status == GroupProductStatus.ACTIVE
        assert product.is_active() is True
        assert product.group_skus == []
        assert product.published_version == 0
        assert product.check_active_references() is False

    def test_disable_transitions_active_to_disabled(
        self, group_product: GroupProductAggregate
    ) -> None:
        assert group_product.status == GroupProductStatus.ACTIVE
        group_product.disable()
        assert group_product.status == GroupProductStatus.DISABLED
        assert group_product.is_active() is False

    def test_enable_transitions_disabled_to_active(
        self, group_product: GroupProductAggregate
    ) -> None:
        group_product.disable()
        assert group_product.status == GroupProductStatus.DISABLED
        group_product.enable()
        assert group_product.status == GroupProductStatus.ACTIVE
        assert group_product.is_active() is True

    def test_disable_idempotent_when_already_disabled(
        self, group_product: GroupProductAggregate
    ) -> None:
        group_product.disable()
        group_product.disable()
        assert group_product.status == GroupProductStatus.DISABLED

    def test_enable_idempotent_when_already_active(
        self, group_product: GroupProductAggregate
    ) -> None:
        group_product.enable()
        assert group_product.status == GroupProductStatus.ACTIVE

    def test_disable_with_active_references_rejected(
        self, group_product: GroupProductAggregate
    ) -> None:
        group_product.mark_has_active_references()
        with pytest.raises(MDMError) as exc:
            group_product.disable()
        assert exc.value.code == MDMErrorCode.GROUP_PRODUCT_HAS_ACTIVE_REFERENCE
        assert group_product.status == GroupProductStatus.ACTIVE
        assert group_product.is_active() is True

    def test_disable_without_active_references_succeeds(
        self, group_product: GroupProductAggregate
    ) -> None:
        assert group_product.check_active_references() is False
        group_product.disable()
        assert group_product.status == GroupProductStatus.DISABLED

    def test_disable_records_disabled_event(
        self, group_product: GroupProductAggregate
    ) -> None:
        group_product.disable()
        events = list(group_product.pull_events())
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, GroupProductDisabledEvent)
        assert event.group_product_id == group_product.id.value
        assert event.group_product_code == "GP-001"
        assert event.change_type == "disable"

    def test_enable_after_disable_does_not_record_event(
        self, group_product: GroupProductAggregate
    ) -> None:
        group_product.disable()
        group_product.clear_events()
        group_product.enable()
        assert list(group_product.pull_events()) == []

    def test_add_group_sku_appends_sku(
        self, group_product: GroupProductAggregate
    ) -> None:
        sku = _make_group_sku(group_product.id, "GS-A")
        group_product.add_group_sku(sku)
        assert len(group_product.group_skus) == 1
        assert group_product.group_skus[0].group_sku_code == "GS-A"

    def test_add_group_sku_duplicate_code_rejected(
        self, group_product: GroupProductAggregate
    ) -> None:
        sku1 = _make_group_sku(group_product.id, "GS-DUP")
        group_product.add_group_sku(sku1)
        sku2 = _make_group_sku(group_product.id, "GS-DUP")
        with pytest.raises(MDMError) as exc:
            group_product.add_group_sku(sku2)
        assert exc.value.code == MDMErrorCode.GROUP_SKU_DUPLICATE
        assert len(group_product.group_skus) == 1

    def test_add_group_sku_mismatched_product_rejected(
        self, group_product: GroupProductAggregate
    ) -> None:
        other_product_id = EntityId.generate()
        sku = _make_group_sku(other_product_id, "GS-X")
        with pytest.raises(MDMError) as exc:
            group_product.add_group_sku(sku)
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID
        assert group_product.group_skus == []

    def test_add_group_sku_records_sku_created_event(
        self, group_product: GroupProductAggregate
    ) -> None:
        sku = _make_group_sku(group_product.id, "GS-EVT")
        group_product.add_group_sku(sku)
        events = list(group_product.pull_events())
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, GroupSkuCreatedEvent)
        assert event.group_product_id == group_product.id.value
        assert event.group_sku_id == sku.group_sku_id.value
        assert event.group_sku_code == "GS-EVT"

    def test_get_group_sku_returns_matching_sku(
        self, group_product: GroupProductAggregate
    ) -> None:
        sku = _make_group_sku(group_product.id, "GS-G")
        group_product.add_group_sku(sku)
        found = group_product.get_group_sku(sku.group_sku_id)
        assert found is not None
        assert found.group_sku_id == sku.group_sku_id

    def test_get_group_sku_returns_none_when_missing(
        self, group_product: GroupProductAggregate
    ) -> None:
        assert group_product.get_group_sku(EntityId.generate()) is None

    def test_publish_requires_active_status(
        self, group_product: GroupProductAggregate
    ) -> None:
        group_product.disable()
        with pytest.raises(MDMError) as exc:
            group_product.publish(new_version=1)
        assert exc.value.code == MDMErrorCode.GROUP_PRODUCT_DISABLED

    def test_publish_rejects_non_increasing_version(
        self, group_product: GroupProductAggregate
    ) -> None:
        group_product.publish(new_version=2)
        with pytest.raises(MDMError) as exc:
            group_product.publish(new_version=2)
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID
        assert group_product.published_version == 2

    def test_publish_records_published_event(
        self, group_product: GroupProductAggregate
    ) -> None:
        group_product.publish(new_version=1)
        events = list(group_product.pull_events())
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, GroupProductPublishedEvent)
        assert event.from_version == 0
        assert event.to_version == 1
        assert event.group_product_code == "GP-001"

    def test_update_name_and_description(self, group_product: GroupProductAggregate) -> None:
        group_product.update_name("新名称")
        group_product.update_description("新描述")
        assert group_product.group_product_name == "新名称"
        assert group_product.description == "新描述"

    def test_update_category_and_brand(self, group_product: GroupProductAggregate) -> None:
        new_category = uuid4()
        new_brand = uuid4()
        group_product.update_category(new_category)
        group_product.update_brand(new_brand)
        assert group_product.group_category_id == new_category
        assert group_product.group_brand_id == new_brand

    def test_update_category_to_none(self, group_product: GroupProductAggregate) -> None:
        group_product.update_category(None)
        assert group_product.group_category_id is None

    def test_properties_access(self) -> None:
        category_id = uuid4()
        brand_id = uuid4()
        spec_template_id = uuid4()
        unit_id = uuid4()
        product = GroupProductAggregate(
            id=EntityId.generate(),
            group_product_code="GP-PA",
            group_product_name="属性访问",
            base_unit_id=unit_id,
            group_category_id=category_id,
            group_brand_id=brand_id,
            spec_template_id=spec_template_id,
            description="属性描述",
        )
        assert product.group_product_code == "GP-PA"
        assert product.group_product_name == "属性访问"
        assert product.base_unit_id == unit_id
        assert product.group_category_id == category_id
        assert product.group_brand_id == brand_id
        assert product.spec_template_id == spec_template_id
        assert product.description == "属性描述"


class GroupSkuTest:
    """集团 SKU 实体 - 全平台全局唯一编码与条码。"""

    def test_sku_defaults_empty_collections(self) -> None:
        sku = _make_group_sku(EntityId.generate(), "GS-D")
        assert sku.specification_instance == {}
        assert sku.barcode_list == []
        assert sku.weight is None
        assert sku.volume is None
        assert sku.status == GroupSkuStatus.ACTIVE
        assert sku.is_active() is True

    def test_sku_disable_enable_state_machine(self) -> None:
        sku = _make_group_sku(EntityId.generate(), "GS-S")
        sku.disable()
        assert sku.status == GroupSkuStatus.DISABLED
        assert sku.is_active() is False
        sku.enable()
        assert sku.status == GroupSkuStatus.ACTIVE
        assert sku.is_active() is True

    def test_add_barcode_appends_unique(self) -> None:
        sku = _make_group_sku(EntityId.generate(), "GS-B", barcode_list=["BC-1"])
        sku.add_barcode("BC-2")
        assert sku.barcode_list == ["BC-1", "BC-2"]
        sku.add_barcode("BC-1")
        assert sku.barcode_list == ["BC-1", "BC-2"]

    def test_update_specification(self) -> None:
        sku = _make_group_sku(EntityId.generate(), "GS-U")
        sku.update_specification({"color": "red", "size": "L"})
        assert sku.specification_instance == {"color": "red", "size": "L"}


class GroupCategoryAggregateTest:
    """集团分类聚合根 - 树形结构禁止循环引用。"""

    def _make_category(
        self,
        code: str = "CAT-ROOT",
        parent_category_id: uuid4 | None = None,
        level: int = 1,
    ) -> GroupCategoryAggregate:
        return GroupCategoryAggregate(
            id=EntityId.generate(),
            group_category_code=code,
            group_category_name=code,
            level=level,
            parent_category_id=parent_category_id,
        )

    def test_create_root_category(self) -> None:
        cat = self._make_category("CAT-ROOT")
        assert cat.parent_category_id is None
        assert cat.level == 1
        assert cat.is_active() is True
        assert cat.children == []

    def test_create_child_category(self) -> None:
        parent_id = uuid4()
        cat = self._make_category("CAT-CHILD", parent_category_id=parent_id, level=2)
        assert cat.parent_category_id == parent_id
        assert cat.level == 2

    def test_add_child_sets_level_and_appends(self) -> None:
        parent = self._make_category("CAT-P")
        child = GroupCategoryAggregate(
            id=EntityId.generate(),
            group_category_code="CAT-C",
            group_category_name="子",
            parent_category_id=parent.id.value,
        )
        parent.add_child(child)
        assert len(parent.children) == 1
        assert parent.children[0].level == parent.level + 1
        assert parent.children[0].group_category_code == "CAT-C"

    def test_add_child_mismatched_parent_rejected(self) -> None:
        parent = self._make_category("CAT-P")
        child = GroupCategoryAggregate(
            id=EntityId.generate(),
            group_category_code="CAT-C",
            group_category_name="子",
            parent_category_id=uuid4(),
        )
        with pytest.raises(MDMError) as exc:
            parent.add_child(child)
        assert exc.value.code == MDMErrorCode.CATEGORY_MULTI_BELONG_DENIED

    def test_add_child_duplicate_code_with_parent_rejected(self) -> None:
        parent = self._make_category("CAT-SAME")
        child = GroupCategoryAggregate(
            id=EntityId.generate(),
            group_category_code="CAT-SAME",
            group_category_name="同名子",
            parent_category_id=parent.id.value,
        )
        with pytest.raises(MDMError) as exc:
            parent.add_child(child)
        assert exc.value.code == MDMErrorCode.CATEGORY_CYCLE

    def test_validate_no_cycle_passes_on_tree(self) -> None:
        root = self._make_category("CAT-R")
        child = GroupCategoryAggregate(
            id=EntityId.generate(),
            group_category_code="CAT-C1",
            group_category_name="子1",
            parent_category_id=root.id.value,
        )
        root.add_child(child)
        grandchild = GroupCategoryAggregate(
            id=EntityId.generate(),
            group_category_code="CAT-C2",
            group_category_name="孙",
            parent_category_id=child.id.value,
        )
        child.add_child(grandchild)
        root.validate_no_cycle()

    def test_validate_no_cycle_detects_self_reference(self) -> None:
        cid = EntityId.generate()
        cat = GroupCategoryAggregate(
            id=cid,
            group_category_code="CAT-CY",
            group_category_name="循环",
            parent_category_id=uuid4(),
        )
        with pytest.raises(MDMError) as exc:
            cat.validate_no_cycle(visited={cid.value})
        assert exc.value.code == MDMErrorCode.CATEGORY_CYCLE

    def test_validate_no_cycle_detects_cycle_in_children(self) -> None:
        root = self._make_category("CAT-R")
        child = GroupCategoryAggregate(
            id=EntityId.generate(),
            group_category_code="CAT-C",
            group_category_name="子",
            parent_category_id=root.id.value,
        )
        root.add_child(child)
        with pytest.raises(MDMError) as exc:
            root.validate_no_cycle(visited={root.id.value, child.id.value})
        assert exc.value.code == MDMErrorCode.CATEGORY_CYCLE

    def test_disable_enable_state_machine(self) -> None:
        cat = self._make_category("CAT-S")
        cat.disable()
        assert cat.status == CategoryStatus.DISABLED
        assert cat.is_active() is False
        cat.enable()
        assert cat.status == CategoryStatus.ACTIVE
        assert cat.is_active() is True

    def test_disable_idempotent(self) -> None:
        cat = self._make_category("CAT-S")
        cat.disable()
        cat.disable()
        assert cat.status == CategoryStatus.DISABLED

    def test_publish_increases_version(self) -> None:
        cat = self._make_category("CAT-P")
        cat.publish(new_version=1)
        assert cat.published_version == 1
        with pytest.raises(MDMError) as exc:
            cat.publish(new_version=1)
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_update_name(self) -> None:
        cat = self._make_category("CAT-N")
        cat.update_name("新分类名")
        assert cat.group_category_name == "新分类名"


class GroupUnitConversionTest:
    """集团单位换算值对象 - 换算率循环/矛盾被拒绝。"""

    def test_create_valid_conversion(self) -> None:
        from_unit = uuid4()
        to_unit = uuid4()
        conv = GroupUnitConversion(
            conversion_id=uuid4(),
            from_unit_id=from_unit,
            to_unit_id=to_unit,
            ratio=Decimal("12.0"),
        )
        assert conv.from_unit_id == from_unit
        assert conv.to_unit_id == to_unit
        assert conv.ratio == Decimal("12.0")

    def test_self_unit_rejected_as_cycle(self) -> None:
        unit = uuid4()
        with pytest.raises(MDMError) as exc:
            GroupUnitConversion(
                conversion_id=uuid4(),
                from_unit_id=unit,
                to_unit_id=unit,
                ratio=Decimal("1.0"),
            )
        assert exc.value.code == MDMErrorCode.UNIT_CONVERSION_CONFLICT

    def test_zero_ratio_rejected(self) -> None:
        with pytest.raises(MDMError) as exc:
            GroupUnitConversion(
                conversion_id=uuid4(),
                from_unit_id=uuid4(),
                to_unit_id=uuid4(),
                ratio=Decimal("0"),
            )
        assert exc.value.code == MDMErrorCode.UNIT_CONVERSION_CONFLICT

    def test_negative_ratio_rejected(self) -> None:
        with pytest.raises(MDMError) as exc:
            GroupUnitConversion(
                conversion_id=uuid4(),
                from_unit_id=uuid4(),
                to_unit_id=uuid4(),
                ratio=Decimal("-1.5"),
            )
        assert exc.value.code == MDMErrorCode.UNIT_CONVERSION_CONFLICT

    def test_inverse_ratio(self) -> None:
        conv = GroupUnitConversion(
            conversion_id=uuid4(),
            from_unit_id=uuid4(),
            to_unit_id=uuid4(),
            ratio=Decimal("10"),
        )
        assert conv.inverse_ratio() == Decimal("0.1")

    def test_is_consistent_with_consistent_inverse(self) -> None:
        unit_a = uuid4()
        unit_b = uuid4()
        ab = GroupUnitConversion(
            conversion_id=uuid4(),
            from_unit_id=unit_a,
            to_unit_id=unit_b,
            ratio=Decimal("2"),
        )
        ba = GroupUnitConversion(
            conversion_id=uuid4(),
            from_unit_id=unit_b,
            to_unit_id=unit_a,
            ratio=Decimal("0.5"),
        )
        assert ab.is_consistent_with(ba) is True

    def test_is_consistent_with_contradictory_inverse_rejected(self) -> None:
        unit_a = uuid4()
        unit_b = uuid4()
        ab = GroupUnitConversion(
            conversion_id=uuid4(),
            from_unit_id=unit_a,
            to_unit_id=unit_b,
            ratio=Decimal("2"),
        )
        contradictory_ba = GroupUnitConversion(
            conversion_id=uuid4(),
            from_unit_id=unit_b,
            to_unit_id=unit_a,
            ratio=Decimal("0.3"),
        )
        assert ab.is_consistent_with(contradictory_ba) is False

    def test_is_consistent_with_unrelated_conversion_returns_true(self) -> None:
        ab = GroupUnitConversion(
            conversion_id=uuid4(),
            from_unit_id=uuid4(),
            to_unit_id=uuid4(),
            ratio=Decimal("2"),
        )
        cd = GroupUnitConversion(
            conversion_id=uuid4(),
            from_unit_id=uuid4(),
            to_unit_id=uuid4(),
            ratio=Decimal("3"),
        )
        assert ab.is_consistent_with(cd) is True

    def test_frozen_value_object_is_immutable(self) -> None:
        conv = GroupUnitConversion(
            conversion_id=uuid4(),
            from_unit_id=uuid4(),
            to_unit_id=uuid4(),
            ratio=Decimal("2"),
        )
        with pytest.raises(AttributeError):
            conv.ratio = Decimal("3")  # type: ignore[misc]