"""集团领域事件 - 业务变更、报表查询、主数据下发、只读越权。"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.shared.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class BusinessChangedEvent(DomainEvent):
    """业务变更事件 - 各 Organization 业务写入时发布，驱动 SummarySnapshot 异步聚合。"""

    tenant_id: UUID
    enterprise_id: UUID
    organization_id: UUID
    dimension: str
    delta: float
    source_version: int


@dataclass(frozen=True, kw_only=True)
class GroupReportQueriedEvent(DomainEvent):
    """集团报表查询事件 - 记录查询维度与延迟标记。"""

    enterprise_id: UUID
    dimension: str
    is_delayed: bool
    organization_count: int


@dataclass(frozen=True, kw_only=True)
class MasterDataPropagatedEvent(DomainEvent):
    """主数据下发事件 - 记录下发结果（成功/失败/冲突）。"""

    enterprise_id: UUID
    master_data_type: str
    master_data_id: str
    succeeded_org_ids: tuple[UUID, ...]
    failed_org_ids: tuple[UUID, ...]
    conflict_org_ids: tuple[UUID, ...]


@dataclass(frozen=True, kw_only=True)
class ReadonlyViolationEvent(DomainEvent):
    """只读越权事件 - 集团管理员对子公司单据执行写操作时发布。"""

    enterprise_id: UUID
    actor_id: UUID
    operation: str
    target_organization_id: UUID