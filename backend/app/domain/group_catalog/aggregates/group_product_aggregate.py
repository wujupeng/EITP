"""集团商品聚合根 - 集团级商品主数据，无 tenant_id（全平台共享）。

禁止贫血模型：所有集团商品行为内聚于聚合根中。
停用时校验是否存在活跃企业引用（spec 5.1.1.7）。
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from uuid import UUID

from app.domain.group_catalog.entities.group_sku import GroupSku, GroupSkuStatus
from app.domain.group_catalog.events.group_catalog_events import (
    GroupProductDisabledEvent,
    GroupProductPublishedEvent,
    GroupSkuCreatedEvent,
)
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode


class GroupProductStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class GroupProductAggregate(AggregateRoot):
    """集团商品聚合根 - 管理集团商品生命周期、集团 SKU 集合、状态。

    集团级无 tenant_id（全平台共享），group_product_code 全平台唯一。
    """

    def __init__(
        self,
        id: EntityId,
        group_product_code: str,
        group_product_name: str,
        base_unit_id: UUID,
        group_category_id: UUID | None = None,
        group_brand_id: UUID | None = None,
        spec_template_id: UUID | None = None,
        description: str | None = None,
        status: GroupProductStatus = GroupProductStatus.ACTIVE,
        published_version: int = 0,
    ) -> None:
        super().__init__(id)
        self._group_product_code = group_product_code
        self._group_product_name = group_product_name
        self._base_unit_id = base_unit_id
        self._group_category_id = group_category_id
        self._group_brand_id = group_brand_id
        self._spec_template_id = spec_template_id
        self._description = description
        self._status = status
        self._published_version = published_version
        self._group_skus: list[GroupSku] = []
        self._has_active_references = False

    @property
    def group_product_code(self) -> str:
        return self._group_product_code

    @property
    def group_product_name(self) -> str:
        return self._group_product_name

    @property
    def base_unit_id(self) -> UUID:
        return self._base_unit_id

    @property
    def group_category_id(self) -> UUID | None:
        return self._group_category_id

    @property
    def group_brand_id(self) -> UUID | None:
        return self._group_brand_id

    @property
    def spec_template_id(self) -> UUID | None:
        return self._spec_template_id

    @property
    def description(self) -> str | None:
        return self._description

    @property
    def status(self) -> GroupProductStatus:
        return self._status

    @property
    def published_version(self) -> int:
        return self._published_version

    @property
    def group_skus(self) -> list[GroupSku]:
        return list(self._group_skus)

    def is_active(self) -> bool:
        return self._status == GroupProductStatus.ACTIVE

    def add_group_sku(self, sku: GroupSku) -> None:
        if sku.group_product_id != self._id:
            raise MDMError(
                MDMErrorCode.SPEC_INSTANCE_INVALID,
                "集团 SKU 所属商品与当前聚合根不一致",
            )
        if any(s.group_sku_code == sku.group_sku_code for s in self._group_skus):
            raise MDMError(
                MDMErrorCode.GROUP_SKU_DUPLICATE,
                f"集团 SKU 编码 {sku.group_sku_code} 已存在",
            )
        self._group_skus.append(sku)
        self._touch()
        self._record_event(
            GroupSkuCreatedEvent(
                group_product_id=self._id.value,
                group_sku_id=sku.group_sku_id.value,
                group_sku_code=sku.group_sku_code,
            )
        )

    def get_group_sku(self, group_sku_id: EntityId) -> Optional[GroupSku]:
        for s in self._group_skus:
            if s.group_sku_id == group_sku_id:
                return s
        return None

    def check_active_references(self) -> bool:
        """检查是否存在活跃企业引用（spec 5.1.1.7）。"""
        return self._has_active_references

    def mark_has_active_references(self) -> None:
        self._has_active_references = True

    def disable(self) -> None:
        if self._status == GroupProductStatus.DISABLED:
            return
        if self._has_active_references:
            raise MDMError(
                MDMErrorCode.GROUP_PRODUCT_HAS_ACTIVE_REFERENCE,
                f"集团商品 {self._group_product_code} 存在活跃企业引用，禁止停用",
            )
        self._status = GroupProductStatus.DISABLED
        self._touch()
        self._record_event(
            GroupProductDisabledEvent(
                group_product_id=self._id.value,
                group_product_code=self._group_product_code,
            )
        )

    def enable(self) -> None:
        if self._status == GroupProductStatus.ACTIVE:
            return
        self._status = GroupProductStatus.ACTIVE
        self._touch()

    def publish(self, new_version: int) -> None:
        if self._status != GroupProductStatus.ACTIVE:
            raise MDMError(
                MDMErrorCode.GROUP_PRODUCT_DISABLED,
                f"集团商品 {self._group_product_code} 已停用，禁止发布",
            )
        if new_version <= self._published_version:
            raise MDMError(
                MDMErrorCode.SPEC_INSTANCE_INVALID,
                f"发布版本号 {new_version} 必须大于当前版本 {self._published_version}",
            )
        old_version = self._published_version
        self._published_version = new_version
        self._touch()
        self._record_event(
            GroupProductPublishedEvent(
                group_product_id=self._id.value,
                group_product_code=self._group_product_code,
                from_version=old_version,
                to_version=new_version,
            )
        )

    def update_name(self, name: str) -> None:
        self._group_product_name = name
        self._touch()

    def update_description(self, description: str) -> None:
        self._description = description
        self._touch()

    def update_category(self, group_category_id: UUID | None) -> None:
        self._group_category_id = group_category_id
        self._touch()

    def update_brand(self, group_brand_id: UUID | None) -> None:
        self._group_brand_id = group_brand_id
        self._touch()