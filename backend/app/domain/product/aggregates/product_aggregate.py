"""商品聚合根 - 商品主数据、SKU 集合、状态管理。

禁止贫血模型：所有商品行为内聚于聚合根中。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from app.domain.inventory.events.inventory_events import ProductStatusChangedEvent
from app.domain.inventory.value_objects.shared import ProductStatus
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import INVError, INVErrorCode


class Sku:
    """SKU 实体 - 库存核算最小单元，ProductAggregate 内部实体。"""

    def __init__(
        self,
        sku_id: EntityId,
        tenant_id: UUID,
        product_id: EntityId,
        sku_code: str,
        sku_name: str,
        unit_id: UUID,
        specification: dict | None = None,
        barcode_list: list[str] | None = None,
        weight: float | None = None,
        volume: float | None = None,
        status: ProductStatus = ProductStatus.ACTIVE,
    ) -> None:
        self._sku_id = sku_id
        self._tenant_id = tenant_id
        self._product_id = product_id
        self._sku_code = sku_code
        self._sku_name = sku_name
        self._unit_id = unit_id
        self._specification = specification or {}
        self._barcode_list = barcode_list or []
        self._weight = weight
        self._volume = volume
        self._status = status

    @property
    def sku_id(self) -> EntityId:
        return self._sku_id

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def product_id(self) -> EntityId:
        return self._product_id

    @property
    def sku_code(self) -> str:
        return self._sku_code

    @property
    def sku_name(self) -> str:
        return self._sku_name

    @property
    def unit_id(self) -> UUID:
        return self._unit_id

    @property
    def specification(self) -> dict:
        return self._specification

    @property
    def barcode_list(self) -> list[str]:
        return self._barcode_list

    @property
    def weight(self) -> float | None:
        return self._weight

    @property
    def volume(self) -> float | None:
        return self._volume

    @property
    def status(self) -> ProductStatus:
        return self._status

    def is_active(self) -> bool:
        return self._status == ProductStatus.ACTIVE


class ProductAggregate(AggregateRoot):
    """商品聚合根 - 管理商品生命周期、SKU 集合、状态。"""

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        product_code: str,
        product_name: str,
        category_id: UUID | None = None,
        brand_id: UUID | None = None,
        base_unit_id: UUID | None = None,
        description: str | None = None,
        status: ProductStatus = ProductStatus.ACTIVE,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._product_code = product_code
        self._product_name = product_name
        self._category_id = category_id
        self._brand_id = brand_id
        self._base_unit_id = base_unit_id
        self._description = description
        self._status = status
        self._skus: list[Sku] = []
        self._has_active_documents = False

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def product_code(self) -> str:
        return self._product_code

    @property
    def product_name(self) -> str:
        return self._product_name

    @property
    def category_id(self) -> UUID | None:
        return self._category_id

    @property
    def brand_id(self) -> UUID | None:
        return self._brand_id

    @property
    def base_unit_id(self) -> UUID | None:
        return self._base_unit_id

    @property
    def description(self) -> str | None:
        return self._description

    @property
    def status(self) -> ProductStatus:
        return self._status

    @property
    def skus(self) -> list[Sku]:
        return list(self._skus)

    def is_active(self) -> bool:
        return self._status == ProductStatus.ACTIVE

    def add_sku(self, sku: Sku) -> None:
        if sku.tenant_id != self._tenant_id:
            raise INVError(INVErrorCode.CROSS_TENANT_REF_DENIED, "SKU 租户与商品租户不一致")
        if any(s.sku_code == sku.sku_code for s in self._skus):
            raise INVError(INVErrorCode.SKU_DUPLICATE, f"SKU 编码 {sku.sku_code} 已存在")
        self._skus.append(sku)
        self._touch()

    def get_sku(self, sku_id: EntityId) -> Optional[Sku]:
        for s in self._skus:
            if s.sku_id == sku_id:
                return s
        return None

    def has_active_documents(self) -> bool:
        return self._has_active_documents

    def mark_has_active_documents(self) -> None:
        self._has_active_documents = True

    def disable(self, force: bool = False) -> None:
        if self._status == ProductStatus.DISABLED:
            return
        if self._has_active_documents and not force:
            raise INVError(
                INVErrorCode.PRODUCT_HAS_ACTIVE_DOCUMENT,
                f"商品 {self._product_code} 存在进行中单据，禁止停用",
            )
        old_status = self._status
        self._status = ProductStatus.DISABLED
        self._touch()
        self._record_event(
            ProductStatusChangedEvent(
                tenant_id=self._tenant_id,
                product_id=self._id.value,
                from_status=old_status.value,
                to_status=self._status.value,
            )
        )

    def enable(self) -> None:
        if self._status == ProductStatus.ACTIVE:
            return
        old_status = self._status
        self._status = ProductStatus.ACTIVE
        self._touch()
        self._record_event(
            ProductStatusChangedEvent(
                tenant_id=self._tenant_id,
                product_id=self._id.value,
                from_status=old_status.value,
                to_status=self._status.value,
            )
        )

    def update_name(self, name: str) -> None:
        self._product_name = name
        self._touch()

    def update_description(self, description: str) -> None:
        self._description = description
        self._touch()