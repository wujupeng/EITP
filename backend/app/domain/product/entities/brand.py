"""品牌实体 - 租户级隔离。"""

from __future__ import annotations

from uuid import UUID

from app.domain.shared.entity import Entity, EntityId


class Brand(Entity):
    """品牌实体 - 租户级隔离。"""

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        brand_code: str,
        brand_name: str,
        logo_url: str | None = None,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._brand_code = brand_code
        self._brand_name = brand_name
        self._logo_url = logo_url

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def brand_code(self) -> str:
        return self._brand_code

    @property
    def brand_name(self) -> str:
        return self._brand_name

    @property
    def logo_url(self) -> str | None:
        return self._logo_url