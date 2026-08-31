"""属性实例校验器 - 商品/SKU 创建/修改时校验属性实例符合属性模板定义。

- 不符合模板定义拒绝创建（EITP_MDM_ATTRIBUTE_INSTANCE_INVALID，spec 5.3.3.2）
- 校验条码跨 SKU 冲突（EITP_MDM_BARCODE_DUPLICATE，spec 5.3.3.4）
"""

from __future__ import annotations

from app.domain.group_catalog.aggregates.attribute_template_aggregate import (
    AttributeTemplateAggregate,
)
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode


class AttributeInstanceValidator:
    """属性实例校验器。"""

    @staticmethod
    def validate(
        template: AttributeTemplateAggregate,
        value: object,
    ) -> bool:
        """校验属性实例符合模板定义。"""
        return template.validate_instance(value)

    @staticmethod
    def validate_batch(
        templates: list[AttributeTemplateAggregate],
        attributes: dict[str, object],
    ) -> bool:
        """批量校验属性实例。"""
        template_map = {t.attribute_name: t for t in templates}

        for attr_name, template in template_map.items():
            value = attributes.get(attr_name)
            AttributeInstanceValidator.validate(template, value)

        for attr_name in attributes:
            if attr_name not in template_map:
                raise MDMError(
                    MDMErrorCode.ATTRIBUTE_INSTANCE_INVALID,
                    f"属性 {attr_name} 不在属性模板定义中",
                )

        return True

    @staticmethod
    def validate_barcode_no_conflict(
        barcode_to_sku: dict[str, str],
        new_barcode: str,
        new_sku_code: str,
    ) -> None:
        """校验条码跨 SKU 冲突（spec 5.3.3.4）。

        Args:
            barcode_to_sku: 已有条码映射 {barcode: sku_code}
            new_barcode: 新增条码
            new_sku_code: 新增条码所属 SKU 编码
        """
        if new_barcode in barcode_to_sku:
            existing_sku = barcode_to_sku[new_barcode]
            if existing_sku != new_sku_code:
                raise MDMError(
                    MDMErrorCode.BARCODE_DUPLICATE,
                    f"条码 {new_barcode} 已被 SKU {existing_sku} 占用，跨 SKU 条码冲突",
                )