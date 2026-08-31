"""集团 SKU 实体 - GroupProductAggregate 内部实体，全平台全局唯一编码。

作为各企业引用的基准 SKU，无 tenant_id（集团级）。
"""

from __future__ import annotations

from enum import Enum
from uuid import UUID

from app.domain.shared.entity import EntityId


class GroupSkuStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class GroupSku:
    """集团 SKU 实体 - 集团商品的最小可库存单元。

    集团 SKU 编码全平台全局唯一（spec 5.1.1.3），作为各企业引用的基准 SKU。
    """

    def __init__(
        self,
        group_sku_id: EntityId,
        group_product_id: EntityId,
        group_sku_code: str,
        group_sku_name: str,
        unit_id: UUID,
        specification_instance: dict | None = None,
        barcode_list: list[str] | None = None,
        weight: float | None = None,
        volume: float | None = None,
        status: GroupSkuStatus = GroupSkuStatus.ACTIVE,
    ) -> None:
        self._group_sku_id = group_sku_id
        self._group_product_id = group_product_id
        self._group_sku_code = group_sku_code
        self._group_sku_name = group_sku_name
        self._unit_id = unit_id
        self._specification_instance = specification_instance or {}
        self._barcode_list = barcode_list or []
        self._weight = weight
        self._volume = volume
        self._status = status

    @property
    def group_sku_id(self) -> EntityId:
        return self._group_sku_id

    @property
    def group_product_id(self) -> EntityId:
        return self._group_product_id

    @property
    def group_sku_code(self) -> str:
        return self._group_sku_code

    @property
    def group_sku_name(self) -> str:
        return self._group_sku_name

    @property
    def unit_id(self) -> UUID:
        return self._unit_id

    @property
    def specification_instance(self) -> dict:
        return self._specification_instance

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
    def status(self) -> GroupSkuStatus:
        return self._status

    def is_active(self) -> bool:
        return self._status == GroupSkuStatus.ACTIVE

    def disable(self) -> None:
        self._status = GroupSkuStatus.DISABLED

    def enable(self) -> None:
        self._status = GroupSkuStatus.ACTIVE

    def add_barcode(self, barcode: str) -> None:
        if barcode not in self._barcode_list:
            self._barcode_list.append(barcode)

    def update_specification(self, spec: dict) -> None:
        self._specification_instance = spec