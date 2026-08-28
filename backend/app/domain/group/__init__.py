"""Group Bounded Context - 集团模式与跨公司报表。"""

from app.domain.group.group_aggregate import (
    GroupAggregate,
    PropagateConflict,
    PropagateResult,
)
from app.domain.group.group_events import (
    BusinessChangedEvent,
    GroupReportQueriedEvent,
    MasterDataPropagatedEvent,
    ReadonlyViolationEvent,
)
from app.domain.group.readonly_boundary import (
    GroupActor,
    OperationType,
    ReadonlyBoundary,
    SubsidiaryIsolationGuard,
)
from app.domain.group.summary_snapshot import ReportDimension, SummarySnapshot

__all__ = [
    "BusinessChangedEvent",
    "GroupActor",
    "GroupAggregate",
    "GroupReportQueriedEvent",
    "MasterDataPropagatedEvent",
    "OperationType",
    "PropagateConflict",
    "PropagateResult",
    "ReadonlyBoundary",
    "ReadonlyViolationEvent",
    "ReportDimension",
    "SubsidiaryIsolationGuard",
    "SummarySnapshot",
]
