"""Placement Bounded Context - 数据放置与迁移策略。"""

from app.domain.placement.migration_state import (
    MigrationPhase,
    MigrationState,
    MigrationStateGuard,
)
from app.domain.placement.placement_manager import (
    PlacementManager,
    TenantScaleMetrics,
)
from app.domain.placement.placement_record import PlacementRecord, PlacementType

__all__ = [
    "MigrationPhase",
    "MigrationState",
    "MigrationStateGuard",
    "PlacementManager",
    "PlacementRecord",
    "PlacementType",
    "TenantScaleMetrics",
]