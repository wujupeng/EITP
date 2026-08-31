"""集团单位换算值对象 - from_unit_id / to_unit_id / ratio。

复用 INV-001 UnitConversion 校验逻辑，换算率不得形成循环或矛盾（spec 5.5.1.3）。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode


@dataclass(frozen=True)
class GroupUnitConversion:
    """集团单位换算值对象 - 不可变。"""

    conversion_id: UUID
    from_unit_id: UUID
    to_unit_id: UUID
    ratio: Decimal

    def __post_init__(self) -> None:
        if self.from_unit_id == self.to_unit_id:
            raise MDMError(
                MDMErrorCode.UNIT_CONVERSION_CONFLICT,
                "换算源单位与目标单位不能相同",
            )
        if self.ratio <= 0:
            raise MDMError(
                MDMErrorCode.UNIT_CONVERSION_CONFLICT,
                "换算率必须大于 0",
            )

    def inverse_ratio(self) -> Decimal:
        """反向换算率。"""
        return Decimal(1) / self.ratio

    def is_consistent_with(self, other: GroupUnitConversion) -> bool:
        """检查与另一条换算是否一致（不矛盾）。

        A→B ratio=2 且 B→A ratio=0.5 为一致；
        A→B ratio=2 且 B→A ratio=0.3 为矛盾。
        """
        if self.from_unit_id == other.to_unit_id and self.to_unit_id == other.from_unit_id:
            expected_inverse = self.inverse_ratio()
            return other.ratio == expected_inverse
        return True