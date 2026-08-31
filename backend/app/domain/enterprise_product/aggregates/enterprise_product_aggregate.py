"""企业商品聚合根 - 引用集团商品，企业级含 tenant_id（租户级隔离）。

引用状态机：active / reference_released / source_disabled。
enterprise_product_name 为空时继承集团商品名称。
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from uuid import UUID

from app.domain.enterprise_product.entities.enterprise_sku import EnterpriseSku
from app.domain.enterprise_product.events.enterprise_product_events import (
    EnterpriseProductReferencedEvent,
    EnterpriseReferenceReleasedEvent,
)
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode


class ReferenceStatus(str, Enum):
    ACTIVE = "active"
    REFERENCE_RELEASED = "reference_released"
    SOURCE_DISABLED = "source_disabled"


class EnterpriseProductAggregate(AggregateRoot):
    """企业商品聚合根 - 引用集团商品，可差异化定制。

    enterprise_product_code 租户内唯一，group_product_id 引用集团商品。
    """

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        group_product_id: UUID,
        enterprise_product_code: str,
        enterprise_product_name: str | None = None,
        enterprise_category_id: UUID | None = None,
        reference_status: ReferenceStatus = ReferenceStatus.ACTIVE,
        published_version: int = 0,
        referenced_by: UUID | None = None,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._group_product_id = group_product_id
        self._enterprise_product_code = enterprise_product_code
        self._enterprise_product_name = enterprise_product_name
        self._enterprise_category_id = enterprise_category_id
        self._reference_status = reference_status
        self._published_version = published_version
        self._referenced_by = referenced_by
        self._enterprise_skus: list[EnterpriseSku] = []
        self._has_active_documents = False

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def group_product_id(self) -> UUID:
        return self._group_product_id

    @property
    def enterprise_product_code(self) -> str:
        return self._enterprise_product_code

    @property
    def enterprise_product_name(self) -> str | None:
        return self._enterprise_product_name

    @property
    def enterprise_category_id(self) -> UUID | None:
        return self._enterprise_category_id

    @property
    def reference_status(self) -> ReferenceStatus:
        return self._reference_status

    @property
    def published_version(self) -> int:
        return self._published_version

    @property
    def referenced_by(self) -> UUID | None:
        return self._referenced_by

    @property
    def enterprise_skus(self) -> list[EnterpriseSku]:
        return list(self._enterprise_skus)

    def is_active(self) -> bool:
        return self._reference_status == ReferenceStatus.ACTIVE

    def resolve_product_name(self, group_product_name: str) -> str:
        """解析有效商品名称：企业级为空时继承集团商品名称。"""
        return self._enterprise_product_name or group_product_name

    def add_enterprise_sku(self, sku: EnterpriseSku) -> None:
        if sku.tenant_id != self._tenant_id:
            raise MDMError(
                MDMErrorCode.CROSS_TENANT_POLICY_DENIED,
                "企业 SKU 租户与商品租户不一致",
            )
        if sku.enterprise_product_id != self._id:
            raise MDMError(
                MDMErrorCode.SPEC_INSTANCE_INVALID,
                "企业 SKU 所属商品与当前聚合根不一致",
            )
        self._enterprise_skus.append(sku)
        self._touch()

    def get_enterprise_sku(self, sku_id: EntityId) -> Optional[EnterpriseSku]:
        for s in self._enterprise_skus:
            if s.enterprise_sku_id == sku_id:
                return s
        return None

    def mark_source_disabled(self) -> None:
        """集团商品停用时，企业商品引用状态变为 source_disabled。"""
        if self._reference_status == ReferenceStatus.SOURCE_DISABLED:
            return
        self._reference_status = ReferenceStatus.SOURCE_DISABLED
        self._touch()

    def disable(self) -> None:
        if self._reference_status != ReferenceStatus.ACTIVE:
            return
        if self._has_active_documents:
            raise MDMError(
                MDMErrorCode.REFERENCE_HAS_ACTIVE_DOCUMENT,
                f"企业商品 {self._enterprise_product_code} 存在进行中单据，禁止停用",
            )
        self._reference_status = ReferenceStatus.REFERENCE_RELEASED
        self._touch()

    def release_reference(self, released_by: UUID) -> None:
        """释放集团商品引用（spec 5.2.1.6）。"""
        if self._reference_status == ReferenceStatus.REFERENCE_RELEASED:
            return
        if self._has_active_documents:
            raise MDMError(
                MDMErrorCode.REFERENCE_HAS_ACTIVE_DOCUMENT,
                f"企业商品 {self._enterprise_product_code} 存在进行中单据，禁止释放引用",
            )
        self._reference_status = ReferenceStatus.REFERENCE_RELEASED
        self._touch()
        self._record_event(
            EnterpriseReferenceReleasedEvent(
                tenant_id=self._tenant_id,
                enterprise_product_id=self._id.value,
                group_product_id=self._group_product_id,
                released_by=released_by,
            )
        )

    def mark_has_active_documents(self) -> None:
        self._has_active_documents = True

    def update_name(self, name: str) -> None:
        self._enterprise_product_name = name
        self._touch()

    def update_category(self, enterprise_category_id: UUID | None) -> None:
        self._enterprise_category_id = enterprise_category_id
        self._touch()

    @classmethod
    def create_reference(
        cls,
        id: EntityId,
        tenant_id: UUID,
        group_product_id: UUID,
        enterprise_product_code: str,
        referenced_by: UUID,
        enterprise_product_name: str | None = None,
        enterprise_category_id: UUID | None = None,
    ) -> EnterpriseProductAggregate:
        """创建企业商品引用（发布 EnterpriseProductReferencedEvent）。"""
        agg = cls(
            id=id,
            tenant_id=tenant_id,
            group_product_id=group_product_id,
            enterprise_product_code=enterprise_product_code,
            enterprise_product_name=enterprise_product_name,
            enterprise_category_id=enterprise_category_id,
            reference_status=ReferenceStatus.ACTIVE,
            referenced_by=referenced_by,
        )
        agg._record_event(
            EnterpriseProductReferencedEvent(
                tenant_id=tenant_id,
                enterprise_product_id=id.value,
                group_product_id=group_product_id,
                referenced_by=referenced_by,
            )
        )
        return agg