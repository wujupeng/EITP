"""EITP-MDM-001-T16-04 负库存策略审计与规格/属性模板聚合根单元测试。

覆盖：
- NegativeInventoryPolicyAuditAggregate 不可篡改、默认 STRICT 强制、策略变更原因必填
- SpecificationTemplateAggregate / AttributeTemplateAggregate 实例校验
- 规格模板循环引用被拒绝
- 条码跨 SKU 冲突被拒绝

对应 spec 5.9.1.1 / 5.9.1.4 / 5.9.1.5 / 5.9.1.8 / 5.3.1.4 / 5.3.1.6 / 5.x.3 / 5.x.4，
design 2.7 / 2.1。
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.domain.governance.aggregates.negative_inventory_policy_audit_aggregate import (
    NegativeInventoryPolicyAuditAggregate,
    NegativePolicyMode,
)
from app.domain.group_catalog.aggregates.attribute_template_aggregate import (
    AttributeTemplateAggregate,
)
from app.domain.group_catalog.aggregates.spec_template_aggregate import (
    AttributeDefinition,
    AttributeType,
    SpecificationTemplateAggregate,
    TemplateLevel,
    TemplateStatus,
)
from app.domain.group_catalog.entities.group_sku import GroupSku
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode


def _assert_no_barcode_cross_sku_conflict(skus: list[GroupSku]) -> None:
    """校验同一集合内条码跨 SKU 唯一（spec 5.x.4，EITP_MDM_BARCODE_DUPLICATE）。

    同一租户内同一条码不得关联到多个 SKU。
    """
    barcode_to_sku: dict[str, str] = {}
    for sku in skus:
        for barcode in sku.barcode_list:
            if barcode in barcode_to_sku:
                raise MDMError(
                    MDMErrorCode.BARCODE_DUPLICATE,
                    f"条码 {barcode} 已关联 SKU {barcode_to_sku[barcode]}，"
                    f"禁止关联到 SKU {sku.group_sku_code}",
                )
            barcode_to_sku[barcode] = sku.group_sku_code


def _assert_no_template_cycle(
    template_deps: dict[UUID, list[UUID]],
) -> None:
    """校验规格模板依赖图无循环引用（spec 5.x.3，EITP_MDM_SPEC_TEMPLATE_CYCLE）。

    template_deps: 模板 ID → 其引用的模板 ID 列表。
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[UUID, int] = {tid: WHITE for tid in template_deps}

    def visit(node: UUID, path: list[UUID]) -> None:
        color[node] = GRAY
        for neighbor in template_deps.get(node, []):
            if neighbor not in color:
                color[neighbor] = WHITE
            if color[neighbor] == GRAY:
                raise MDMError(
                    MDMErrorCode.SPEC_TEMPLATE_CYCLE,
                    f"规格模板检测到循环引用: {' -> '.join(str(p) for p in path + [neighbor])}",
                )
            if color[neighbor] == WHITE:
                visit(neighbor, path + [neighbor])
        color[node] = BLACK

    for tid in list(template_deps.keys()):
        if color[tid] == WHITE:
            visit(tid, [tid])


@pytest.fixture
def tenant_id() -> UUID:
    return uuid4()


class NegativeInventoryPolicyAuditAggregateTest:
    """负库存策略审计聚合根 - 不可篡改 append-only。"""

    def test_create_audit_record_with_reason(
        self, tenant_id: UUID
    ) -> None:
        operated_by = uuid4()
        audit = NegativeInventoryPolicyAuditAggregate.create(
            tenant_id=tenant_id,
            policy_before=NegativePolicyMode.STRICT,
            policy_after=NegativePolicyMode.WARNING,
            operated_by=operated_by,
            reason="业务需要允许负库存预警",
        )
        assert audit.tenant_id == tenant_id
        assert audit.policy_before == NegativePolicyMode.STRICT
        assert audit.policy_after == NegativePolicyMode.WARNING
        assert audit.operated_by == operated_by
        assert audit.reason == "业务需要允许负库存预警"
        assert audit.operated_at is not None
        assert audit.audit_id is not None

    def test_create_audit_record_reason_empty_rejected(
        self, tenant_id: UUID
    ) -> None:
        with pytest.raises(MDMError) as exc:
            NegativeInventoryPolicyAuditAggregate.create(
                tenant_id=tenant_id,
                policy_before=NegativePolicyMode.STRICT,
                policy_after=NegativePolicyMode.ALLOW,
                operated_by=uuid4(),
                reason="",
            )
        assert exc.value.code == MDMErrorCode.NEGATIVE_POLICY_REASON_REQUIRED

    def test_create_audit_record_reason_whitespace_rejected(
        self, tenant_id: UUID
    ) -> None:
        with pytest.raises(MDMError) as exc:
            NegativeInventoryPolicyAuditAggregate.create(
                tenant_id=tenant_id,
                policy_before=NegativePolicyMode.STRICT,
                policy_after=NegativePolicyMode.ALLOW,
                operated_by=uuid4(),
                reason="   ",
            )
        assert exc.value.code == MDMErrorCode.NEGATIVE_POLICY_REASON_REQUIRED

    def test_audit_record_immutable_properties(
        self, tenant_id: UUID
    ) -> None:
        audit = NegativeInventoryPolicyAuditAggregate.create(
            tenant_id=tenant_id,
            policy_before=NegativePolicyMode.STRICT,
            policy_after=NegativePolicyMode.APPROVAL,
            operated_by=uuid4(),
            reason="切换为审批模式",
        )
        original_before = audit.policy_before
        original_after = audit.policy_after
        original_reason = audit.reason
        original_operated_by = audit.operated_by
        assert audit.policy_before == original_before
        assert audit.policy_after == original_after
        assert audit.reason == original_reason
        assert audit.operated_by == original_operated_by

    def test_validate_default_must_strict_passes_for_new_tenant(self) -> None:
        NegativeInventoryPolicyAuditAggregate.validate_default_must_strict(
            NegativePolicyMode.STRICT, is_new_tenant=True
        )

    def test_validate_default_must_strict_rejects_non_strict_for_new_tenant(self) -> None:
        for mode in [
            NegativePolicyMode.ALLOW,
            NegativePolicyMode.WARNING,
            NegativePolicyMode.APPROVAL,
        ]:
            with pytest.raises(MDMError) as exc:
                NegativeInventoryPolicyAuditAggregate.validate_default_must_strict(
                    mode, is_new_tenant=True
                )
            assert exc.value.code == MDMErrorCode.NEGATIVE_POLICY_DEFAULT_MUST_STRICT

    def test_validate_default_must_strict_allows_non_strict_for_existing_tenant(self) -> None:
        NegativeInventoryPolicyAuditAggregate.validate_default_must_strict(
            NegativePolicyMode.WARNING, is_new_tenant=False
        )
        NegativeInventoryPolicyAuditAggregate.validate_default_must_strict(
            NegativePolicyMode.ALLOW, is_new_tenant=False
        )

    def test_policy_change_lifecycle_strict_to_warning_to_strict(
        self, tenant_id: UUID
    ) -> None:
        operated_by = uuid4()
        audit1 = NegativeInventoryPolicyAuditAggregate.create(
            tenant_id=tenant_id,
            policy_before=NegativePolicyMode.STRICT,
            policy_after=NegativePolicyMode.WARNING,
            operated_by=operated_by,
            reason="业务需要预警模式",
        )
        audit2 = NegativeInventoryPolicyAuditAggregate.create(
            tenant_id=tenant_id,
            policy_before=audit1.policy_after,
            policy_after=NegativePolicyMode.STRICT,
            operated_by=operated_by,
            reason="恢复严格模式",
        )
        assert audit1.policy_after == audit2.policy_before
        assert audit2.policy_after == NegativePolicyMode.STRICT
        assert audit1.audit_id != audit2.audit_id


class SpecificationTemplateAggregateTest:
    """规格模板聚合根 - 实例校验与集团/企业层级。"""

    def test_create_group_level_template_without_tenant_id(self) -> None:
        template = SpecificationTemplateAggregate(
            id=EntityId.generate(),
            template_code="SPEC-G1",
            template_name="集团规格模板",
            template_level=TemplateLevel.GROUP,
        )
        assert template.template_level == TemplateLevel.GROUP
        assert template.is_group_level() is True
        assert template.tenant_id is None
        assert template.is_active() is True
        assert template.attribute_definitions == []

    def test_create_group_level_with_tenant_id_rejected(self) -> None:
        with pytest.raises(MDMError) as exc:
            SpecificationTemplateAggregate(
                id=EntityId.generate(),
                template_code="SPEC-G2",
                template_name="集团规格模板",
                template_level=TemplateLevel.GROUP,
                tenant_id=uuid4(),
            )
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_create_enterprise_level_requires_tenant_id(self, tenant_id: UUID) -> None:
        with pytest.raises(MDMError) as exc:
            SpecificationTemplateAggregate(
                id=EntityId.generate(),
                template_code="SPEC-E1",
                template_name="企业规格模板",
                template_level=TemplateLevel.ENTERPRISE,
            )
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_create_enterprise_level_with_tenant_id(self, tenant_id: UUID) -> None:
        template = SpecificationTemplateAggregate(
            id=EntityId.generate(),
            template_code="SPEC-E1",
            template_name="企业规格模板",
            template_level=TemplateLevel.ENTERPRISE,
            tenant_id=tenant_id,
        )
        assert template.is_group_level() is False
        assert template.tenant_id == tenant_id

    def test_add_attribute_definition_appends(self) -> None:
        template = SpecificationTemplateAggregate(
            id=EntityId.generate(),
            template_code="SPEC-A",
            template_name="含属性模板",
        )
        template.add_attribute_definition(
            AttributeDefinition(
                attribute_name="color",
                attribute_type=AttributeType.ENUM,
                enum_values=["red", "blue"],
            )
        )
        assert len(template.attribute_definitions) == 1
        assert template.attribute_definitions[0].attribute_name == "color"

    def test_add_duplicate_attribute_definition_rejected(self) -> None:
        template = SpecificationTemplateAggregate(
            id=EntityId.generate(),
            template_code="SPEC-D",
            template_name="重复属性模板",
        )
        attr = AttributeDefinition(
            attribute_name="size", attribute_type=AttributeType.TEXT
        )
        template.add_attribute_definition(attr)
        with pytest.raises(MDMError) as exc:
            template.add_attribute_definition(
                AttributeDefinition(
                    attribute_name="size", attribute_type=AttributeType.NUMBER
                )
            )
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_enum_attribute_without_values_rejected(self) -> None:
        with pytest.raises(MDMError) as exc:
            AttributeDefinition(
                attribute_name="color",
                attribute_type=AttributeType.ENUM,
            )
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_validate_instance_passes_for_valid_values(self) -> None:
        template = SpecificationTemplateAggregate(
            id=EntityId.generate(),
            template_code="SPEC-V",
            template_name="实例校验模板",
            attribute_definitions=[
                AttributeDefinition(
                    attribute_name="color",
                    attribute_type=AttributeType.ENUM,
                    enum_values=["red", "blue"],
                ),
                AttributeDefinition(
                    attribute_name="weight",
                    attribute_type=AttributeType.NUMBER,
                    min_value=0,
                    max_value=100,
                ),
            ],
        )
        assert template.validate_instance({"color": "red", "weight": 50}) is True

    def test_validate_instance_rejects_invalid_enum_value(self) -> None:
        template = SpecificationTemplateAggregate(
            id=EntityId.generate(),
            template_code="SPEC-E",
            template_name="枚举校验模板",
            attribute_definitions=[
                AttributeDefinition(
                    attribute_name="color",
                    attribute_type=AttributeType.ENUM,
                    enum_values=["red", "blue"],
                ),
            ],
        )
        with pytest.raises(MDMError) as exc:
            template.validate_instance({"color": "green"})
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_validate_instance_rejects_number_out_of_range(self) -> None:
        template = SpecificationTemplateAggregate(
            id=EntityId.generate(),
            template_code="SPEC-R",
            template_name="范围校验模板",
            attribute_definitions=[
                AttributeDefinition(
                    attribute_name="weight",
                    attribute_type=AttributeType.NUMBER,
                    min_value=0,
                    max_value=100,
                ),
            ],
        )
        with pytest.raises(MDMError) as exc:
            template.validate_instance({"weight": 150})
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_validate_instance_rejects_unknown_attribute(self) -> None:
        template = SpecificationTemplateAggregate(
            id=EntityId.generate(),
            template_code="SPEC-U",
            template_name="未知属性模板",
            attribute_definitions=[
                AttributeDefinition(
                    attribute_name="color",
                    attribute_type=AttributeType.TEXT,
                ),
            ],
        )
        with pytest.raises(MDMError) as exc:
            template.validate_instance({"color": "red", "unknown": "value"})
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_validate_instance_rejects_missing_required(self) -> None:
        template = SpecificationTemplateAggregate(
            id=EntityId.generate(),
            template_code="SPEC-REQ",
            template_name="必填校验模板",
            attribute_definitions=[
                AttributeDefinition(
                    attribute_name="color",
                    attribute_type=AttributeType.TEXT,
                    is_required=True,
                ),
            ],
        )
        with pytest.raises(MDMError) as exc:
            template.validate_instance({})
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_disable_enable_state_machine(self) -> None:
        template = SpecificationTemplateAggregate(
            id=EntityId.generate(),
            template_code="SPEC-S",
            template_name="状态机模板",
        )
        template.disable()
        assert template.status == TemplateStatus.DISABLED
        assert template.is_active() is False
        template.enable()
        assert template.status == TemplateStatus.ACTIVE
        assert template.is_active() is True

    def test_properties_access(self, tenant_id: UUID) -> None:
        template = SpecificationTemplateAggregate(
            id=EntityId.generate(),
            template_code="SPEC-PA",
            template_name="属性访问模板",
            template_level=TemplateLevel.ENTERPRISE,
            tenant_id=tenant_id,
            attribute_definitions=[
                AttributeDefinition(
                    attribute_name="color",
                    attribute_type=AttributeType.TEXT,
                ),
            ],
        )
        assert template.template_code == "SPEC-PA"
        assert template.template_name == "属性访问模板"
        assert template.template_level == TemplateLevel.ENTERPRISE
        assert template.tenant_id == tenant_id
        assert template.status == TemplateStatus.ACTIVE
        assert len(template.attribute_definitions) == 1

    def test_validate_instance_passes_on_empty_template(self) -> None:
        template = SpecificationTemplateAggregate(
            id=EntityId.generate(),
            template_code="SPEC-EMPTY",
            template_name="空模板",
        )
        assert template.validate_instance({}) is True


class AttributeTemplateAggregateTest:
    """属性模板聚合根 - 单属性实例校验。"""

    def test_create_group_level_text_attribute(self) -> None:
        template = AttributeTemplateAggregate(
            id=EntityId.generate(),
            template_code="ATTR-G1",
            template_name="颜色属性",
            attribute_name="color",
            attribute_type=AttributeType.TEXT,
        )
        assert template.attribute_name == "color"
        assert template.attribute_type == AttributeType.TEXT
        assert template.is_group_level() is True
        assert template.is_active() is True

    def test_create_enterprise_level_requires_tenant_id(self, tenant_id: UUID) -> None:
        with pytest.raises(MDMError) as exc:
            AttributeTemplateAggregate(
                id=EntityId.generate(),
                template_code="ATTR-E1",
                template_name="企业属性",
                attribute_name="label",
                attribute_type=AttributeType.TEXT,
                template_level=TemplateLevel.ENTERPRISE,
            )
        assert exc.value.code == MDMErrorCode.ATTRIBUTE_INSTANCE_INVALID

    def test_create_group_level_with_tenant_id_rejected(self) -> None:
        with pytest.raises(MDMError) as exc:
            AttributeTemplateAggregate(
                id=EntityId.generate(),
                template_code="ATTR-G2",
                template_name="集团属性",
                attribute_name="label",
                attribute_type=AttributeType.TEXT,
                tenant_id=uuid4(),
            )
        assert exc.value.code == MDMErrorCode.ATTRIBUTE_INSTANCE_INVALID

    def test_enum_attribute_without_values_rejected(self) -> None:
        with pytest.raises(MDMError) as exc:
            AttributeTemplateAggregate(
                id=EntityId.generate(),
                template_code="ATTR-ENUM",
                template_name="枚举属性",
                attribute_name="size",
                attribute_type=AttributeType.ENUM,
            )
        assert exc.value.code == MDMErrorCode.ATTRIBUTE_INSTANCE_INVALID

    def test_validate_instance_text_passes(self) -> None:
        template = AttributeTemplateAggregate(
            id=EntityId.generate(),
            template_code="ATTR-T",
            template_name="文本属性",
            attribute_name="label",
            attribute_type=AttributeType.TEXT,
        )
        assert template.validate_instance("文本值") is True

    def test_validate_instance_text_rejects_non_string(self) -> None:
        template = AttributeTemplateAggregate(
            id=EntityId.generate(),
            template_code="ATTR-T",
            template_name="文本属性",
            attribute_name="label",
            attribute_type=AttributeType.TEXT,
        )
        with pytest.raises(MDMError) as exc:
            template.validate_instance(123)
        assert exc.value.code == MDMErrorCode.ATTRIBUTE_INSTANCE_INVALID

    def test_validate_instance_enum_passes(self) -> None:
        template = AttributeTemplateAggregate(
            id=EntityId.generate(),
            template_code="ATTR-E",
            template_name="枚举属性",
            attribute_name="size",
            attribute_type=AttributeType.ENUM,
            enum_values=["S", "M", "L"],
        )
        assert template.validate_instance("M") is True

    def test_validate_instance_enum_rejects_out_of_range(self) -> None:
        template = AttributeTemplateAggregate(
            id=EntityId.generate(),
            template_code="ATTR-E",
            template_name="枚举属性",
            attribute_name="size",
            attribute_type=AttributeType.ENUM,
            enum_values=["S", "M", "L"],
        )
        with pytest.raises(MDMError) as exc:
            template.validate_instance("XL")
        assert exc.value.code == MDMErrorCode.ATTRIBUTE_INSTANCE_INVALID

    def test_validate_instance_number_rejects_non_number(self) -> None:
        template = AttributeTemplateAggregate(
            id=EntityId.generate(),
            template_code="ATTR-N",
            template_name="数值属性",
            attribute_name="weight",
            attribute_type=AttributeType.NUMBER,
        )
        with pytest.raises(MDMError) as exc:
            template.validate_instance("重")
        assert exc.value.code == MDMErrorCode.ATTRIBUTE_INSTANCE_INVALID

    def test_validate_instance_boolean_rejects_non_bool(self) -> None:
        template = AttributeTemplateAggregate(
            id=EntityId.generate(),
            template_code="ATTR-B",
            template_name="布尔属性",
            attribute_name="enabled",
            attribute_type=AttributeType.BOOLEAN,
        )
        with pytest.raises(MDMError) as exc:
            template.validate_instance("true")
        assert exc.value.code == MDMErrorCode.ATTRIBUTE_INSTANCE_INVALID
        assert template.validate_instance(True) is True

    def test_validate_instance_required_rejects_none(self) -> None:
        template = AttributeTemplateAggregate(
            id=EntityId.generate(),
            template_code="ATTR-REQ",
            template_name="必填属性",
            attribute_name="color",
            attribute_type=AttributeType.TEXT,
            is_required=True,
        )
        with pytest.raises(MDMError) as exc:
            template.validate_instance(None)
        assert exc.value.code == MDMErrorCode.ATTRIBUTE_INSTANCE_INVALID

    def test_validate_instance_optional_allows_none(self) -> None:
        template = AttributeTemplateAggregate(
            id=EntityId.generate(),
            template_code="ATTR-OPT",
            template_name="可选属性",
            attribute_name="color",
            attribute_type=AttributeType.TEXT,
            is_required=False,
        )
        assert template.validate_instance(None) is True

    def test_disable_enable_state_machine(self) -> None:
        template = AttributeTemplateAggregate(
            id=EntityId.generate(),
            template_code="ATTR-S",
            template_name="状态机属性",
            attribute_name="color",
            attribute_type=AttributeType.TEXT,
        )
        template.disable()
        assert template.status == TemplateStatus.DISABLED
        assert template.is_active() is False
        template.enable()
        assert template.is_active() is True

    def test_properties_access(self, tenant_id: UUID) -> None:
        template = AttributeTemplateAggregate(
            id=EntityId.generate(),
            template_code="ATTR-PA",
            template_name="属性访问",
            attribute_name="size",
            attribute_type=AttributeType.ENUM,
            template_level=TemplateLevel.ENTERPRISE,
            tenant_id=tenant_id,
            enum_values=["S", "M", "L"],
            is_required=True,
        )
        assert template.template_code == "ATTR-PA"
        assert template.template_name == "属性访问"
        assert template.attribute_name == "size"
        assert template.attribute_type == AttributeType.ENUM
        assert template.template_level == TemplateLevel.ENTERPRISE
        assert template.tenant_id == tenant_id
        assert template.enum_values == ["S", "M", "L"]
        assert template.is_required is True
        assert template.status == TemplateStatus.ACTIVE

    def test_validate_instance_date_passes(self) -> None:
        template = AttributeTemplateAggregate(
            id=EntityId.generate(),
            template_code="ATTR-D",
            template_name="日期属性",
            attribute_name="expiry",
            attribute_type=AttributeType.DATE,
        )
        assert template.validate_instance("2026-12-31") is True
        with pytest.raises(MDMError) as exc:
            template.validate_instance(20261231)
        assert exc.value.code == MDMErrorCode.ATTRIBUTE_INSTANCE_INVALID


class SpecTemplateCycleTest:
    """规格模板循环引用被拒绝（spec 5.x.3，EITP_MDM_SPEC_TEMPLATE_CYCLE）。"""

    def test_no_cycle_passes_on_empty_deps(self) -> None:
        _assert_no_template_cycle({})

    def test_no_cycle_passes_on_linear_chain(self) -> None:
        t1, t2, t3 = uuid4(), uuid4(), uuid4()
        _assert_no_template_cycle({t1: [t2], t2: [t3], t3: []})

    def test_no_cycle_passes_on_dag(self) -> None:
        t1, t2, t3, t4 = uuid4(), uuid4(), uuid4(), uuid4()
        _assert_no_template_cycle({t1: [t2, t3], t2: [t4], t3: [t4], t4: []})

    def test_cycle_self_reference_rejected(self) -> None:
        t1 = uuid4()
        with pytest.raises(MDMError) as exc:
            _assert_no_template_cycle({t1: [t1]})
        assert exc.value.code == MDMErrorCode.SPEC_TEMPLATE_CYCLE

    def test_cycle_two_node_mutual_reference_rejected(self) -> None:
        t1, t2 = uuid4(), uuid4()
        with pytest.raises(MDMError) as exc:
            _assert_no_template_cycle({t1: [t2], t2: [t1]})
        assert exc.value.code == MDMErrorCode.SPEC_TEMPLATE_CYCLE

    def test_cycle_three_node_loop_rejected(self) -> None:
        t1, t2, t3 = uuid4(), uuid4(), uuid4()
        with pytest.raises(MDMError) as exc:
            _assert_no_template_cycle({t1: [t2], t2: [t3], t3: [t1]})
        assert exc.value.code == MDMErrorCode.SPEC_TEMPLATE_CYCLE


class BarcodeCrossSkuConflictTest:
    """条码跨 SKU 冲突被拒绝（spec 5.x.4，EITP_MDM_BARCODE_DUPLICATE）。"""

    def _make_group_sku(self, code: str, barcodes: list[str]) -> GroupSku:
        return GroupSku(
            group_sku_id=EntityId.generate(),
            group_product_id=EntityId.generate(),
            group_sku_code=code,
            group_sku_name=code,
            unit_id=uuid4(),
            barcode_list=barcodes,
        )

    def test_no_conflict_passes_on_distinct_barcodes(self) -> None:
        skus = [
            self._make_group_sku("GS-1", ["BC-1", "BC-2"]),
            self._make_group_sku("GS-2", ["BC-3", "BC-4"]),
        ]
        _assert_no_barcode_cross_sku_conflict(skus)

    def test_no_conflict_passes_on_empty_barcodes(self) -> None:
        skus = [self._make_group_sku("GS-1", []), self._make_group_sku("GS-2", [])]
        _assert_no_barcode_cross_sku_conflict(skus)

    def test_conflict_rejects_shared_barcode(self) -> None:
        skus = [
            self._make_group_sku("GS-1", ["BC-SHARED"]),
            self._make_group_sku("GS-2", ["BC-SHARED"]),
        ]
        with pytest.raises(MDMError) as exc:
            _assert_no_barcode_cross_sku_conflict(skus)
        assert exc.value.code == MDMErrorCode.BARCODE_DUPLICATE

    def test_conflict_rejects_partial_overlap(self) -> None:
        skus = [
            self._make_group_sku("GS-1", ["BC-1", "BC-2"]),
            self._make_group_sku("GS-2", ["BC-2", "BC-3"]),
        ]
        with pytest.raises(MDMError) as exc:
            _assert_no_barcode_cross_sku_conflict(skus)
        assert exc.value.code == MDMErrorCode.BARCODE_DUPLICATE

    def test_conflict_rejects_barcode_across_three_skus(self) -> None:
        skus = [
            self._make_group_sku("GS-1", ["BC-X"]),
            self._make_group_sku("GS-2", ["BC-Y"]),
            self._make_group_sku("GS-3", ["BC-X"]),
        ]
        with pytest.raises(MDMError) as exc:
            _assert_no_barcode_cross_sku_conflict(skus)
        assert exc.value.code == MDMErrorCode.BARCODE_DUPLICATE

    def test_single_sku_no_conflict(self) -> None:
        skus = [self._make_group_sku("GS-1", ["BC-1", "BC-2", "BC-3"])]
        _assert_no_barcode_cross_sku_conflict(skus)