"""集团品牌实体 - 全平台唯一编码，无 tenant_id（集团级）。"""

from __future__ import annotations

from enum import Enum

from app.domain.shared.entity import EntityId


class BrandStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class GroupBrand:
    """集团品牌实体 - 全平台唯一编码。"""

    def __init__(
        self,
        group_brand_id: EntityId,
        group_brand_code: str,
        group_brand_name: str,
        status: BrandStatus = BrandStatus.ACTIVE,
        description: str | None = None,
    ) -> None:
        self._group_brand_id = group_brand_id
        self._group_brand_code = group_brand_code
        self._group_brand_name = group_brand_name
        self._status = status
        self._description = description

    @property
    def group_brand_id(self) -> EntityId:
        return self._group_brand_id

    @property
    def group_brand_code(self) -> str:
        return self._group_brand_code

    @property
    def group_brand_name(self) -> str:
        return self._group_brand_name

    @property
    def status(self) -> BrandStatus:
        return self._status

    @property
    def description(self) -> str | None:
        return self._description

    def is_active(self) -> bool:
        return self._status == BrandStatus.ACTIVE

    def disable(self) -> None:
        self._status = BrandStatus.DISABLED

    def enable(self) -> None:
        self._status = BrandStatus.ACTIVE