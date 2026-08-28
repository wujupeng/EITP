"""集团聚合根 - 跨公司汇总与主数据下发的一致性边界。

spec 5.6 / design 2.3.2.6。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.domain.group.group_events import (
    BusinessChangedEvent,
    GroupReportQueriedEvent,
    MasterDataPropagatedEvent,
)
from app.domain.group.readonly_boundary import (
    GroupActor,
    OperationType,
    ReadonlyBoundary,
)
from app.domain.group.summary_snapshot import ReportDimension, SummarySnapshot
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import ErrorCode, GroupError

_SNAPSHOT_DELAY_THRESHOLD_SECONDS = 300
_AGGREGATION_TIMEOUT_SECONDS = 3.0


@dataclass(frozen=True)
class PropagateConflict:
    """主数据下发冲突记录。"""

    organization_id: UUID
    master_data_id: str
    reason: str


@dataclass(frozen=True)
class PropagateResult:
    """主数据下发结果。"""

    master_data_type: str
    master_data_id: str
    succeeded: tuple[UUID, ...]
    failed: tuple[UUID, ...]
    conflicts: tuple[PropagateConflict, ...]

    @property
    def has_conflict(self) -> bool:
        return len(self.conflicts) > 0

    @property
    def has_failure(self) -> bool:
        return len(self.failed) > 0


class GroupAggregate(AggregateRoot):
    """集团聚合根 - 管理一个 Enterprise 下所有 Organization 的汇总与下发。

    职责：
    - 维护子公司列表
    - 跨公司汇总报表（优先读 SummarySnapshot，延迟标记 is_delayed）
    - 集团主数据下发（保留公司级属性，编码冲突暂停）
    - 只读边界校验
    """

    def __init__(self, id: EntityId, enterprise_id: UUID) -> None:
        super().__init__(id)
        self._enterprise_id = enterprise_id
        self._organizations: set[UUID] = set()
        self._snapshots: dict[tuple[UUID, ReportDimension], SummarySnapshot] = {}

    @property
    def enterprise_id(self) -> UUID:
        return self._enterprise_id

    @property
    def organizations(self) -> frozenset[UUID]:
        return frozenset(self._organizations)

    def add_organization(self, organization_id: UUID) -> None:
        """添加子公司。"""
        self._organizations.add(organization_id)

    def remove_organization(self, organization_id: UUID) -> None:
        """移除子公司。"""
        self._organizations.discard(organization_id)

    def enforce_readonly(
        self,
        actor: GroupActor,
        operation: OperationType,
        target_organization_id: UUID,
    ) -> None:
        """委托 ReadonlyBoundary 强制只读边界。"""
        ReadonlyBoundary.enforce(actor, operation, target_organization_id)

    def update_snapshot(self, snapshot: SummarySnapshot) -> None:
        """更新汇总快照（由异步消费者调用）。"""
        if snapshot.enterprise_id != self._enterprise_id:
            raise GroupError(
                ErrorCode.GROUP_READONLY_VIOLATION,
                "快照 enterprise_id 与聚合不匹配",
            )
        self._snapshots[(snapshot.organization_id, snapshot.dimension)] = snapshot

    def get_snapshot(
        self,
        organization_id: UUID,
        dimension: ReportDimension,
    ) -> SummarySnapshot | None:
        return self._snapshots.get((organization_id, dimension))

    def aggregate_report(
        self,
        dimension: ReportDimension,
        organization_ids: tuple[UUID, ...] | None = None,
        now: datetime | None = None,
    ) -> tuple[dict, bool, int]:
        """跨公司汇总报表。

        Args:
            dimension: 报表维度
            organization_ids: 指定汇总的子公司列表，None 表示全部
            now: 当前时间（测试注入）

        Returns:
            (汇总值, is_delayed, 组织数)
        """
        now = now or datetime.now(timezone.utc)
        target_orgs = organization_ids or tuple(self._organizations)

        merged_value: dict = {}
        is_delayed = False
        org_count = 0

        for org_id in target_orgs:
            snapshot = self._snapshots.get((org_id, dimension))
            if snapshot is None:
                continue
            org_count += 1
            if snapshot.is_delayed(now, _SNAPSHOT_DELAY_THRESHOLD_SECONDS):
                is_delayed = True
            for key, value in snapshot.snapshot_value.items():
                if key in merged_value and isinstance(merged_value[key], (int, float)) and isinstance(value, (int, float)):
                    merged_value[key] = merged_value[key] + value
                else:
                    merged_value[key] = value

        self._record_event(
            GroupReportQueriedEvent(
                enterprise_id=self._enterprise_id,
                dimension=dimension.value,
                is_delayed=is_delayed,
                organization_count=org_count,
            )
        )

        return merged_value, is_delayed, org_count

    def propagate_master_data(
        self,
        master_data_type: str,
        master_data_id: str,
        target_org_ids: tuple[UUID, ...],
        existing_codes: dict[UUID, set[str]] | None = None,
    ) -> PropagateResult:
        """集团主数据下发至子公司。

        Rules:
        - 保留公司级属性（不覆盖）
        - 编码冲突暂停下发（EITP_MT_MASTER_DATA_CONFLICT）
        - 下发失败标记并可重试（EITP_MT_MASTER_PROPAGATE_FAILED）

        Args:
            existing_codes: 各子公司已有编码集合，用于冲突检测
        """
        existing_codes = existing_codes or {}
        succeeded: list[UUID] = []
        failed: list[UUID] = []
        conflicts: list[PropagateConflict] = []

        for org_id in target_org_ids:
            org_codes = existing_codes.get(org_id, set())
            if master_data_id in org_codes:
                conflicts.append(
                    PropagateConflict(
                        organization_id=org_id,
                        master_data_id=master_data_id,
                        reason="编码与子公司已有主数据冲突",
                    )
                )
                continue
            if org_id not in self._organizations:
                failed.append(org_id)
                continue
            succeeded.append(org_id)

        result = PropagateResult(
            master_data_type=master_data_type,
            master_data_id=master_data_id,
            succeeded=tuple(succeeded),
            failed=tuple(failed),
            conflicts=tuple(conflicts),
        )

        self._record_event(
            MasterDataPropagatedEvent(
                enterprise_id=self._enterprise_id,
                master_data_type=master_data_type,
                master_data_id=master_data_id,
                succeeded_org_ids=result.succeeded,
                failed_org_ids=result.failed,
                conflict_org_ids=tuple(c.organization_id for c in result.conflicts),
            )
        )

        return result

    def publish_business_changed(
        self,
        organization_id: UUID,
        dimension: ReportDimension,
        delta: float,
        source_version: int,
        tenant_id: UUID,
    ) -> BusinessChangedEvent:
        """发布业务变更事件 - 驱动 SummarySnapshot 异步聚合。"""
        event = BusinessChangedEvent(
            tenant_id=tenant_id,
            enterprise_id=self._enterprise_id,
            organization_id=organization_id,
            dimension=dimension.value,
            delta=delta,
            source_version=source_version,
        )
        self._record_event(event)
        return event

    @staticmethod
    def snapshot_delay_threshold() -> int:
        """快照延迟阈值（秒）。"""
        return _SNAPSHOT_DELAY_THRESHOLD_SECONDS

    @staticmethod
    def aggregation_timeout() -> float:
        """跨公司汇总超时阈值（秒，C-PERF-03）。"""
        return _AGGREGATION_TIMEOUT_SECONDS