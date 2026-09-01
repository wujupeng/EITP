"""SAL PackingRecordAggregate 聚合根 - 包装记录。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.sales.entities.packing_line import PackingLine
from app.domain.sales.value_objects.shipment_vo import PackingStatus
from app.interfaces.middleware.error_handler import SALError, SALErrorCode


@dataclass
class PackingRecordAggregate:
    """包装记录聚合根 - 装箱明细 + 毛重/净重/体积汇总 + 包装件数。"""

    packing_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    shipment_id: UUID = field(default_factory=uuid4)
    package_count: int = 0
    total_gross_weight: float = 0.0
    total_net_weight: float = 0.0
    total_volume: float = 0.0
    lines: list[PackingLine] = field(default_factory=list)
    status: PackingStatus = PackingStatus.DRAFT
    packed_by: UUID | None = None
    packed_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_line(self, line: PackingLine) -> None:
        """添加装箱明细。"""
        line.packing_id = self.packing_id
        self.lines.append(line)

    def calculate_summary(self) -> None:
        """汇总毛重/净重/体积/包装件数，系统计算。"""
        self.total_gross_weight = round(sum(line.gross_weight for line in self.lines), 2)
        self.total_net_weight = round(sum(line.net_weight for line in self.lines), 2)
        self.total_volume = round(sum(line.volume for line in self.lines), 2)
        self.package_count = len({line.carton_no for line in self.lines if line.carton_no})

    def mark_packed(self, packed_by: UUID) -> None:
        """标记包装完成。"""
        if self.status != PackingStatus.DRAFT:
            raise SALError(SALErrorCode.SHIPMENT_ORDER_INVALID, "包装记录非草稿状态不可完成")
        if not self.lines:
            raise SALError(SALErrorCode.SHIPMENT_NOT_FOUND, "包装记录无明细行")
        self.calculate_summary()
        self.status = PackingStatus.PACKED
        self.packed_by = packed_by
        self.packed_at = datetime.now(timezone.utc)

    def cancel(self) -> None:
        """取消包装。"""
        if self.status != PackingStatus.DRAFT:
            raise SALError(SALErrorCode.SHIPMENT_ORDER_INVALID, "包装记录非草稿状态不可取消")
        self.status = PackingStatus.CANCELLED