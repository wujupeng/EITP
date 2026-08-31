"""属性模板聚合根 - 定义单个属性的类型与约束。

集团级模板全平台统一（tenant_id 为空），企业级模板仅本企业生效（含 tenant_id）。
企业级属性模板可补充集团属性模板未覆盖的场景（spec 5.3.1.8）。
"""

from __future__ import annotations

from uuid import UUID

from app.domain.group_catalog.aggregates.spec_template_aggregate import (
    AttributeType,
    TemplateLevel,
    TemplateStatus,
)
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode


class AttributeTemplateAggregate(AggregateRoot):
    """属性模板聚合根 - 定义单个属性的类型与约束。"""

    def __init__(
        self,
        id: EntityId,
        template_code: str,
        template_name: str,
        attribute_name: str,
        attribute_type: AttributeType,
        template_level: TemplateLevel = TemplateLevel.GROUP,
        tenant_id: UUID | None = None,
        enum_values: list[str] | None = None,
        is_required: bool = False,
        status: TemplateStatus = TemplateStatus.ACTIVE,
    ) -> None:
        super().__init__(id)
        if template_level == TemplateLevel.GROUP and tenant_id is not None:
            raise MDMError(
                MDMErrorCode.ATTRIBUTE_INSTANCE_INVALID,
                "集团级模板不能含 tenant_id",
            )
        if template_level == TemplateLevel.ENTERPRISE and tenant_id is None:
            raise MDMError(
                MDMErrorCode.ATTRIBUTE_INSTANCE_INVALID,
                "企业级模板必须含 tenant_id",
            )
        if attribute_type == AttributeType.ENUM and not enum_values:
            raise MDMError(
                MDMErrorCode.ATTRIBUTE_INSTANCE_INVALID,
                f"枚举属性 {attribute_name} 必须指定 enum_values",
            )
        self._template_code = template_code
        self._template_name = template_name
        self._attribute_name = attribute_name
        self._attribute_type = attribute_type
        self._template_level = template_level
        self._tenant_id = tenant_id
        self._enum_values = enum_values or []
        self._is_required = is_required
        self._status = status

    @property
    def template_code(self) -> str:
        return self._template_code

    @property
    def template_name(self) -> str:
        return self._template_name

    @property
    def attribute_name(self) -> str:
        return self._attribute_name

    @property
    def attribute_type(self) -> AttributeType:
        return self._attribute_type

    @property
    def template_level(self) -> TemplateLevel:
        return self._template_level

    @property
    def tenant_id(self) -> UUID | None:
        return self._tenant_id

    @property
    def enum_values(self) -> list[str]:
        return self._enum_values

    @property
    def is_required(self) -> bool:
        return self._is_required

    @property
    def status(self) -> TemplateStatus:
        return self._status

    def is_active(self) -> bool:
        return self._status == TemplateStatus.ACTIVE

    def is_group_level(self) -> bool:
        return self._template_level == TemplateLevel.GROUP

    def validate_instance(self, value: object) -> bool:
        """校验属性实例符合模板定义（spec 5.3.1.6）。"""
        if value is None:
            if self._is_required:
                raise MDMError(
                    MDMErrorCode.ATTRIBUTE_INSTANCE_INVALID,
                    f"属性 {self._attribute_name} 为必填项",
                )
            return True

        if self._attribute_type == AttributeType.TEXT:
            if not isinstance(value, str):
                raise MDMError(
                    MDMErrorCode.ATTRIBUTE_INSTANCE_INVALID,
                    f"属性 {self._attribute_name} 要求文本类型",
                )
        elif self._attribute_type == AttributeType.NUMBER:
            if not isinstance(value, (int, float)):
                raise MDMError(
                    MDMErrorCode.ATTRIBUTE_INSTANCE_INVALID,
                    f"属性 {self._attribute_name} 要求数值类型",
                )
        elif self._attribute_type == AttributeType.ENUM:
            if str(value) not in self._enum_values:
                raise MDMError(
                    MDMErrorCode.ATTRIBUTE_INSTANCE_INVALID,
                    f"属性 {self._attribute_name} 的值 {value} 不在枚举范围 {self._enum_values} 内",
                )
        elif self._attribute_type == AttributeType.BOOLEAN:
            if not isinstance(value, bool):
                raise MDMError(
                    MDMErrorCode.ATTRIBUTE_INSTANCE_INVALID,
                    f"属性 {self._attribute_name} 要求布尔类型",
                )
        elif self._attribute_type == AttributeType.DATE:
            if not isinstance(value, str):
                raise MDMError(
                    MDMErrorCode.ATTRIBUTE_INSTANCE_INVALID,
                    f"属性 {self._attribute_name} 要求日期字符串类型",
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