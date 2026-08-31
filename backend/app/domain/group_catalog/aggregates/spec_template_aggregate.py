"""规格模板聚合根 - 定义 SKU 规格属性的结构与约束。

集团级模板全平台统一（tenant_id 为空），企业级模板仅本企业生效（含 tenant_id）。
"""

from __future__ import annotations

from enum import Enum
from uuid import UUID

from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode


class TemplateLevel(str, Enum):
    GROUP = "group"
    ENTERPRISE = "enterprise"


class TemplateStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class AttributeType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    ENUM = "enum"
    DATE = "date"
    BOOLEAN = "boolean"


class AttributeDefinition:
    """规格模板中的属性定义项。"""

    def __init__(
        self,
        attribute_name: str,
        attribute_type: AttributeType,
        is_required: bool = False,
        enum_values: list[str] | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> None:
        self._attribute_name = attribute_name
        self._attribute_type = attribute_type
        self._is_required = is_required
        self._enum_values = enum_values or []
        self._min_value = min_value
        self._max_value = max_value

        if attribute_type == AttributeType.ENUM and not self._enum_values:
            raise MDMError(
                MDMErrorCode.SPEC_INSTANCE_INVALID,
                f"枚举属性 {attribute_name} 必须指定 enum_values",
            )

    @property
    def attribute_name(self) -> str:
        return self._attribute_name

    @property
    def attribute_type(self) -> AttributeType:
        return self._attribute_type

    @property
    def is_required(self) -> bool:
        return self._is_required

    @property
    def enum_values(self) -> list[str]:
        return self._enum_values

    @property
    def min_value(self) -> float | None:
        return self._min_value

    @property
    def max_value(self) -> float | None:
        return self._max_value

    def validate_value(self, value: object) -> bool:
        """校验值是否符合属性定义。"""
        if value is None:
            return not self._is_required

        if self._attribute_type == AttributeType.TEXT:
            return isinstance(value, str)
        elif self._attribute_type == AttributeType.NUMBER:
            if not isinstance(value, (int, float)):
                return False
            if self._min_value is not None and value < self._min_value:
                return False
            if self._max_value is not None and value > self._max_value:
                return False
            return True
        elif self._attribute_type == AttributeType.ENUM:
            return str(value) in self._enum_values
        elif self._attribute_type == AttributeType.DATE:
            return isinstance(value, str)
        elif self._attribute_type == AttributeType.BOOLEAN:
            return isinstance(value, bool)
        return False


class SpecificationTemplateAggregate(AggregateRoot):
    """规格模板聚合根 - 定义 SKU 规格属性的结构。

    template_code 集团级全平台唯一或企业级租户内唯一。
    """

    def __init__(
        self,
        id: EntityId,
        template_code: str,
        template_name: str,
        template_level: TemplateLevel = TemplateLevel.GROUP,
        tenant_id: UUID | None = None,
        status: TemplateStatus = TemplateStatus.ACTIVE,
        attribute_definitions: list[AttributeDefinition] | None = None,
    ) -> None:
        super().__init__(id)
        if template_level == TemplateLevel.GROUP and tenant_id is not None:
            raise MDMError(
                MDMErrorCode.SPEC_INSTANCE_INVALID,
                "集团级模板不能含 tenant_id",
            )
        if template_level == TemplateLevel.ENTERPRISE and tenant_id is None:
            raise MDMError(
                MDMErrorCode.SPEC_INSTANCE_INVALID,
                "企业级模板必须含 tenant_id",
            )
        self._template_code = template_code
        self._template_name = template_name
        self._template_level = template_level
        self._tenant_id = tenant_id
        self._status = status
        self._attribute_definitions = attribute_definitions or []

    @property
    def template_code(self) -> str:
        return self._template_code

    @property
    def template_name(self) -> str:
        return self._template_name

    @property
    def template_level(self) -> TemplateLevel:
        return self._template_level

    @property
    def tenant_id(self) -> UUID | None:
        return self._tenant_id

    @property
    def status(self) -> TemplateStatus:
        return self._status

    @property
    def attribute_definitions(self) -> list[AttributeDefinition]:
        return list(self._attribute_definitions)

    def is_active(self) -> bool:
        return self._status == TemplateStatus.ACTIVE

    def is_group_level(self) -> bool:
        return self._template_level == TemplateLevel.GROUP

    def add_attribute_definition(self, attr_def: AttributeDefinition) -> None:
        if any(a.attribute_name == attr_def.attribute_name for a in self._attribute_definitions):
            raise MDMError(
                MDMErrorCode.SPEC_INSTANCE_INVALID,
                f"属性 {attr_def.attribute_name} 已存在",
            )
        self._attribute_definitions.append(attr_def)
        self._touch()

    def validate_instance(self, instance: dict) -> bool:
        """校验规格实例符合模板定义（spec 5.3.1.4）。"""
        attr_map = {a.attribute_name: a for a in self._attribute_definitions}

        for attr_name, attr_def in attr_map.items():
            value = instance.get(attr_name)
            if not attr_def.validate_value(value):
                raise MDMError(
                    MDMErrorCode.SPEC_INSTANCE_INVALID,
                    f"规格属性 {attr_name} 的值 {value} 不符合模板定义",
                )

        for key in instance:
            if key not in attr_map:
                raise MDMError(
                    MDMErrorCode.SPEC_INSTANCE_INVALID,
                    f"规格属性 {key} 不在模板定义中",
                )

        return True

    def disable(self) -> None:
        if self._status == TemplateStatus.DISABLED:
            return
        self._status = TemplateStatus.DISABLED
        self._touch()

    def enable(self) -> None:
        if self._status == TemplateStatus.ACTIVE:
            return
        self._status = TemplateStatus.ACTIVE
        self._touch()