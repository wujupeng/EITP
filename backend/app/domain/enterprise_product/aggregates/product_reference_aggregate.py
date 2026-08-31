"""商品引用关系聚合根 - 企业引用集团商品的引用关系。

复合唯一约束（tenant_id, group_product_id）：同一企业不可重复引用同一集团商品（spec 5.2.3.5）。
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from app.domain.enterprise_product.aggregates.enterprise_product_aggregate import (
    ReferenceStatus,
)
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode


class ProductReferenceAggregate(AggregateRoot):
    """商品引用关系聚合根 - 企业→集团商品引用。

    引用状态：active / released / source_disabled。
    """

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        group_product_id: UUID,
        enterprise_product_id: UUID,
        referenced_by: UUID,
        referenced_at: datetime | None = None,
        reference_status: ReferenceStatus = ReferenceStatus.ACTIVE,
        released_by: UUID | None = None,
        released_at: datetime | None = None,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._group_product_id = group_product_id
        self._enterprise_product_id = enterprise_product_id
        self._referenced_by = referenced_by
        self._referenced_at = referenced_at or datetime.now(timezone.utc)
        self._reference_status = reference_status
        self._released_by = released_by
        self._released_at = released_at

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def group_product_id(self) -> UUID:
        return self._group_product_id

    @property
    def enterprise_product_id(self) -> UUID:
        return self._enterprise_product_id

    @property
    def referenced_by(self) -> UUID:
        return self._referenced_by

    @property
    def referenced_at(self) -> datetime:
        return self._referenced_at

    @property
    def reference_status(self) -> ReferenceStatus:
        return self._reference_status

    @property
    def released_by(self) -> UUID | None:
        return self._released_by

    @property
    def released_at(self) -> datetime | None:
        return self._released_at

    def is_active(self) -> bool:
        return self._reference_status == ReferenceStatus.ACTIVE

    def release(self, released_by: UUID) -> None:
        """释放引用关系。"""
        if self._reference_status == ReferenceStatus.REFERENCE_RELEASED:
            return
        self._reference_status = ReferenceStatus.REFERENCE_RELEASED
        self._released_by = released_by
        self._released_at = datetime.now(timezone.utc)
        self._touch()

    def mark_source_disabled(self) -> None:
        """集团商品停用时，引用关系变为 source_disabled。"""
        if self._reference_status == ReferenceStatus.SOURCE_DISABLED:
            return
        self._reference_status = ReferenceStatus.SOURCE_DISABLED
        self._touch()

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        group_product_id: UUID,
        enterprise_product_id: UUID,
        referenced_by: UUID,
    ) -> ProductReferenceAggregate:
        return cls(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            group_product_id=group_product_id,
            enterprise_product_id=enterprise_product_id,
            referenced_by=referenced_by,
        )

    @staticmethod
    def validate_no_duplicate(
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