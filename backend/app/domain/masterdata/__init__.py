"""MasterData Bounded Context - 主数据层级继承（集团基准 → 公司级覆盖 → 仓库级覆盖）。"""

from app.domain.masterdata.master_data_base import MasterDataBase
from app.domain.masterdata.master_data_events import (
    CompanyOverrideUpdatedEvent,
    MasterDataBaseChangedEvent,
    MasterDataBaseCreatedEvent,
    WarehouseOverrideUpdatedEvent,
)
from app.domain.masterdata.overrides import CompanyOverride, WarehouseOverride
from app.domain.masterdata.permission_guard import MasterDataPermissionGuard

__all__ = [
    "CompanyOverride",
    "CompanyOverrideUpdatedEvent",
    "MasterDataBase",
    "MasterDataBaseChangedEvent",
    "MasterDataBaseCreatedEvent",
    "MasterDataPermissionGuard",
    "WarehouseOverride",
    "WarehouseOverrideUpdatedEvent",
]