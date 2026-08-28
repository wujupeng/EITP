"""主数据领域事件 - 基准创建/变更、覆盖维护、下发。"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.shared.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class MasterDataBaseCreatedEvent(DomainEvent):
    """集团主数据基准创建事件。"""

    enterprise_id: UUID
    master_data_id: UUID
    sku_code: str
    version: int


@dataclass(frozen=True, kw_only=True)
class MasterDataBaseChangedEvent(DomainEvent):
    """集团主数据基准变更事件 - 触发下发。"""

    enterprise_id: UUID
    master_data_id: UUID
    sku_code: str
    old_version: int
    new_version: int


@dataclass(frozen=True, kw_only=True)
class CompanyOverrideUpdatedEvent(DomainEvent):
    """公司级属性覆盖更新事件。"""

    master_data_id: UUID
    organization_id: UUID
    changed_keys: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class WarehouseOverrideUpdatedEvent(DomainEvent):
    """仓库级属性覆盖更新事件。"""

    master_data_id: UUID
    warehouse_id: UUID
    changed_keys: tuple[str, ...]