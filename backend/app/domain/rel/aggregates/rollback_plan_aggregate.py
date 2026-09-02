"""REL 回滚方案聚合根 - RollbackPlanAggregate。"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.rel.enums import DrillStatus
from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError


@dataclass(frozen=True)
class RollbackPlanAggregate:
    """回滚方案聚合根 - 仅演练状态字段可更新，其余字段不可变。"""

    rollback_id: UUID
    release_id: UUID
    version_rollback_sop: dict
    database_rollback_migrations: list[dict]
    config_rollback_plan: dict
    plan_hash: str
    drill_status: DrillStatus = DrillStatus.NOT_DRILLED
    drill_result: dict | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        release_id: UUID,
        version_rollback_sop: dict,
        database_rollback_migrations: list[dict],
        config_rollback_plan: dict,
        plan_hash: str,
    ) -> RollbackPlanAggregate:
        return cls(
            rollback_id=uuid4(),
            release_id=release_id,
            version_rollback_sop=version_rollback_sop,
            database_rollback_migrations=database_rollback_migrations,
            config_rollback_plan=config_rollback_plan,
            plan_hash=plan_hash,
        )

    def mark_drill_pass(self, result: dict) -> RollbackPlanAggregate:
        if self.drill_status != DrillStatus.NOT_DRILLED:
            raise RELError(
                RELErrorCode.ROLLBACK_DRILL_FAILED,
                f"drill already completed, status={self.drill_status.value}",
            )
        return replace(
            self,
            drill_status=DrillStatus.DRILLED_PASS,
            drill_result=result,
            updated_at=datetime.now(timezone.utc),
        )

    def mark_drill_fail(self, result: dict) -> RollbackPlanAggregate:
        if self.drill_status != DrillStatus.NOT_DRILLED:
            raise RELError(
                RELErrorCode.ROLLBACK_DRILL_FAILED,
                f"drill already completed, status={self.drill_status.value}",
            )
        return replace(
            self,
            drill_status=DrillStatus.DRILLED_FAIL,
            drill_result=result,
            updated_at=datetime.now(timezone.utc),
        )