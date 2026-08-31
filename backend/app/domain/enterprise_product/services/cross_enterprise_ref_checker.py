"""跨企业引用校验器 - 校验企业引用集团商品的合法性。

- 引用的集团商品已发布且未停用（spec 5.7.1.8）
- 跨企业直接引用企业商品被拒绝（spec 5.2.1.9）
- 跨企业共享必须通过集团商品目录（spec 5.7.1.7）
- 重复引用同一集团商品被拒绝（spec 5.2.3.5）
"""

from __future__ import annotations

from uuid import UUID

from app.domain.group_catalog.aggregates.group_product_aggregate import (
    GroupProductAggregate,
    GroupProductStatus,
)
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode


class CrossEnterpriseRefChecker:
    """跨企业引用校验器。"""

    @staticmethod
    def validate_group_product_available(
        group_product: GroupProductAggregate,
    ) -> None:
        """校验集团商品已发布且未停用（spec 5.7.1.8）。"""
        if group_product.status != GroupProductStatus.ACTIVE:
            raise MDMError(
                MDMErrorCode.GROUP_PRODUCT_DISABLED,
                f"集团商品 {group_product.group_product_code} 已停用，禁止引用",
            )
        if group_product.published_version == 0:
            raise MDMError(
                MDMErrorCode.GROUP_PRODUCT_NOT_PUBLISHED,
                f"集团商品 {group_product.group_product_code} 尚未发布，禁止引用",
            )

    @staticmethod
    def validate_no_cross_enterprise_direct_ref(
        source_tenant_id: UUID,
        target_tenant_id: UUID,
    ) -> None:
        """校验跨企业直接引用企业商品被拒绝（spec 5.2.1.9）。

        跨企业共享必须通过集团商品目录（spec 5.7.1.7）。
        """
        if source_tenant_id != target_tenant_id:
            raise MDMError(
                MDMErrorCode.CROSS_ENTERPRISE_REF_DENIED,
                "禁止跨企业直接引用企业商品，跨企业共享必须通过集团商品目录",
            )

    @staticmethod
    def validate_no_duplicate_reference(
        existing_refs: list[tuple[UUID, UUID]],
        tenant_id: UUID,
        group_product_id: UUID,
    ) -> None:
        """校验同一企业不可重复引用同一集团商品（spec 5.2.3.5）。"""
        for ref_tenant, ref_group in existing_refs:
            if ref_tenant == tenant_id and ref_group == group_product_id:
                raise MDMError(
                    MDMErrorCode.DUPLICATE_REFERENCE,
                    "同一企业已引用该集团商品，禁止重复引用",
                )

    @staticmethod
    def validate_reference_creation(
        group_product: GroupProductAggregate,
        tenant_id: UUID,
        existing_refs: list[tuple[UUID, UUID]],
    ) -> None:
        """综合校验引用创建的合法性。"""
        CrossEnterpriseRefChecker.validate_group_product_available(group_product)
        CrossEnterpriseRefChecker.validate_no_duplicate_reference(
            existing_refs, tenant_id, group_product.id.value
        )