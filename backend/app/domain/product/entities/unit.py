"""计量单位实体 - 基本单位与换算率。"""

from __future__ import annotations

from uuid import UUID

from app.domain.shared.entity import Entity, EntityId


class Unit(Entity):
    """计量单位实体 - is_base_unit 标记基本单位。"""

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        unit_code: str,
        unit_name: str,
        is_base_unit: bool = False,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._unit_code = unit_code
        self._unit_name = unit_name
        self._is_base_unit = is_base_unit

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def unit_code(self) -> str:
        return self._unit_code

    @property
    def unit_name(self) -> str:
        return self._unit_name

    @property
    def is_base_unit(self) -> bool:
        return self._is_base_unit