"""单位换算值对象 - 换算率不得形成循环或矛盾。"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class UnitConversion:
    """单位换算值对象 - from_unit → to_unit 的换算率。"""

    from_unit_id: UUID
    to_unit_id: UUID
    ratio: float

    def __post_init__(self) -> None:
        if self.ratio <= 0:
            raise ValueError("换算率必须为正数")
        if self.from_unit_id == self.to_unit_id:
            raise ValueError("源单位与目标单位不能相同")

    def inverse(self) -> UnitConversion:
        return UnitConversion(
            from_unit_id=self.to_unit_id,
            to_unit_id=self.from_unit_id,
            ratio=1.0 / self.ratio,
        )

    def compose(self, other: UnitConversion) -> UnitConversion:
        if self.to_unit_id != other.from_unit_id:
            raise ValueError("换算链不连续")
        return UnitConversion(
            from_unit_id=self.from_unit_id,
            to_unit_id=other.to_unit_id,
            ratio=self.ratio * other.ratio,
        )