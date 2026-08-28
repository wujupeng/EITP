"""迁移状态与写入冻结守卫。

spec 5.7.3 / C-MIG-02: 迁移中冻结该租户写入。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from uuid import UUID

from app.interfaces.middleware.error_handler import ErrorCode, GroupError

_DEFAULT_TIMEOUT = timedelta(minutes=30)


class MigrationPhase(str, Enum):
    """迁移阶段 - 四阶段编排。"""

    PENDING = "pending"
    FREEZING = "freezing"
    FULL_SYNC = "full_sync"
    INCREMENTAL_SYNC = "incremental_sync"
    VERIFYING = "verifying"
    SWITCHING = "switching"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

    @property
    def is_write_frozen(self) -> bool:
        """该阶段是否冻结写入。"""
        return self in {
            MigrationPhase.FREEZING,
            MigrationPhase.FULL_SYNC,
            MigrationPhase.INCREMENTAL_SYNC,
            MigrationPhase.VERIFYING,
            MigrationPhase.SWITCHING,
        }


@dataclass
class MigrationState:
    """迁移状态 - 追踪迁移任务进度。

    四阶段：冻结写入 → 全量同步 → 增量同步（WAL）→ 数据校验 → 原子切换 → 恢复写入
    """

    task_id: UUID
    tenant_id: UUID
    target_placement: str
    phase: MigrationPhase = MigrationPhase.PENDING
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    failure_reason: str | None = None
    progress_percent: float = 0.0

    def advance_to(self, phase: MigrationPhase) -> None:
        """推进到下一阶段。"""
        self.phase = phase
        if phase == MigrationPhase.COMPLETED:
            self.completed_at = datetime.now(timezone.utc)
            self.progress_percent = 100.0
        elif phase == MigrationPhase.FREEZING:
            self.progress_percent = 10.0
        elif phase == MigrationPhase.FULL_SYNC:
            self.progress_percent = 30.0
        elif phase == MigrationPhase.INCREMENTAL_SYNC:
            self.progress_percent = 60.0
        elif phase == MigrationPhase.VERIFYING:
            self.progress_percent = 80.0
        elif phase == MigrationPhase.SWITCHING:
            self.progress_percent = 90.0

    def fail(self, reason: str) -> None:
        """标记迁移失败。"""
        self.phase = MigrationPhase.FAILED
        self.failure_reason = reason
        self.completed_at = datetime.now(timezone.utc)

    def rollback(self) -> None:
        """回滚迁移。"""
        self.phase = MigrationPhase.ROLLED_BACK
        self.completed_at = datetime.now(timezone.utc)

    def is_write_frozen(self) -> bool:
        """当前是否冻结写入。"""
        return self.phase.is_write_frozen

    def is_timed_out(
        self,
        now: datetime | None = None,
        timeout: timedelta = _DEFAULT_TIMEOUT,
    ) -> bool:
        """是否超时。"""
        now = now or datetime.now(timezone.utc)
        return (now - self.started_at) > timeout


class MigrationStateGuard:
    """迁移状态守卫 - 拒绝迁移中的写入操作。

    C-MIG-02: 迁移中冻结该租户写入。
    """

    @staticmethod
    def enforce_not_frozen(
        tenant_id: UUID,
        migration_state: MigrationState | None,
    ) -> None:
        """校验租户未处于迁移冻结状态。

        Raises:
            GroupError: EITP_MT_MIGRATION_IN_PROGRESS
        """
        if migration_state is not None and migration_state.is_write_frozen():
            raise GroupError(
                ErrorCode.MIGRATION_IN_PROGRESS,
                "租户迁移进行中，业务写入被冻结",
                details={
                    "tenant_id": str(tenant_id),
                    "phase": migration_state.phase.value,
                    "task_id": str(migration_state.task_id),
                },
            )

    @staticmethod
    def enforce_not_timed_out(
        migration_state: MigrationState,
        now: datetime | None = None,
    ) -> None:
        """校验迁移未超时。

        Raises:
            GroupError: EITP_MT_MIGRATION_TIMEOUT
        """
        if migration_state.is_timed_out(now):
            raise GroupError(
                ErrorCode.MIGRATION_TIMEOUT,
                "迁移任务超时",
                details={
                    "task_id": str(migration_state.task_id),
                    "started_at": migration_state.started_at.isoformat(),
                },
            )