"""集团单位实体 - is_base_unit 标记基本单位，无 tenant_id（集团级）。"""

from __future__ import annotations

from enum import Enum

from app.domain.shared.entity import EntityId


class UnitStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class GroupUnit:
    """集团单位实体 - 计量单位（个/箱/千克等）。"""

    def __init__(
        self,
        group_unit_id: EntityId,
        group_unit_code: str,
        group_unit_name: str,
        is_base_unit: bool = False,
        status: UnitStatus = UnitStatus.ACTIVE,
    ) -> None:
        self._group_unit_id = group_unit_id
        self._group_unit_code = group_unit_code
        self._group_unit_name = group_unit_name
        self._is_base_unit = is_base_unit
        self._status = status

    @property
    def group_unit_id(self) -> EntityId:
        return self._group_unit_id

    @property
    def group_unit_code(self) -> str:
        return self._group_unit_code

    @property
    def group_unit_name(self) -> str:
        return self._group_unit_name

    @property
    def is_base_unit(self) -> bool:
        return self._is_base_unit

    @property
    def status(self) -> UnitStatus:
        return self._status

    def is_active(self) -> bool:
        return self._status == UnitStatus.ACTIVE