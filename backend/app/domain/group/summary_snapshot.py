"""汇总快照值对象 - 跨公司汇总的最终一致缓存。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class ReportDimension(str, Enum):
    """报表维度 - 销售额/采购额/库存/资金/客户/供应商。"""

    SALES = "sales"
    PURCHASE = "purchase"
    INVENTORY = "inventory"
    FUNDS = "funds"
    CUSTOMER = "customer"
    SUPPLIER = "supplier"


@dataclass(frozen=True)
class SummarySnapshot:
    """汇总快照 - 单个 Organization 单个维度的聚合缓存。

    时效策略（spec 5.6.3.2）：
    - snapshot_at 距今 >5 分钟标记 is_delayed=true
    - 由异步消费者消费 BusinessChangedEvent 更新，最终一致 ≤5 分钟
    """

    snapshot_id: UUID
    enterprise_id: UUID
    organization_id: UUID
    dimension: ReportDimension
    snapshot_value: dict
    snapshot_at: datetime
    source_version: int

    @classmethod
    def create(
        cls,
        enterprise_id: UUID,
        organization_id: UUID,
        dimension: ReportDimension,
        snapshot_value: dict,
        source_version: int = 0,
        snapshot_at: datetime | None = None,
    ) -> SummarySnapshot:
        return cls(
            snapshot_id=uuid4(),
            enterprise_id=enterprise_id,
            organization_id=organization_id,
            dimension=dimension,
            snapshot_value=snapshot_value,
            snapshot_at=snapshot_at or datetime.now(timezone.utc),
            source_version=source_version,
        )

    def is_delayed(
        self,
        now: datetime | None = None,
        threshold_seconds: int = 300,
    ) -> bool:
        """检查快照是否延迟超限（默认 5 分钟）。"""
        now = now or datetime.now(timezone.utc)
        elapsed = (now - self.snapshot_at).total_seconds()
        return elapsed > threshold_seconds

    def merge(self, other: SummarySnapshot) -> dict:
        """合并两个快照的值（用于跨公司汇总）。"""
        merged = dict(self.snapshot_value)
        for key, value in other.snapshot_value.items():
            if key in merged and isinstance(merged[key], (int, float)) and isinstance(value, (int, float)):
                merged[key] = merged[key] + value
            else:
                merged[key] = value
        return merged