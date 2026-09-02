"""Saga 实例聚合根 - 分布式事务编排。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class SagaStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPENSATING = "COMPENSATING"
    COMPENSATED = "COMPENSATED"
    FAILED = "FAILED"
    MANUAL_INTERVENTION = "MANUAL_INTERVENTION"


@dataclass(frozen=True)
class SagaInstanceAggregate:
    """Saga 实例聚合根 - 编排分布式事务步骤与补偿。"""

    saga_id: UUID
    saga_type: str
    tenant_id: UUID
    status: SagaStatus
    current_step: int
    steps: list[dict]
    compensations: list[dict]
    trace_id: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        saga_type: str,
        tenant_id: UUID,
        steps: list[dict],
        trace_id: str,
    ) -> SagaInstanceAggregate:
        now = datetime.now(timezone.utc)
        return cls(
            saga_id=uuid4(),
            saga_type=saga_type,
            tenant_id=tenant_id,
            status=SagaStatus.RUNNING,
            current_step=0,
            steps=steps,
            compensations=[],
            trace_id=trace_id,
            created_at=now,
            updated_at=now,
        )

    def advance_step(self) -> SagaInstanceAggregate:
        next_step = self.current_step + 1
        if next_step >= len(self.steps):
            return self._with(status=SagaStatus.COMPLETED, current_step=next_step)
        return self._with(current_step=next_step)

    def start_compensation(self) -> SagaInstanceAggregate:
        return self._with(status=SagaStatus.COMPENSATING)

    def complete_compensation(self) -> SagaInstanceAggregate:
        return self._with(status=SagaStatus.COMPENSATED)

    def fail(self, reason: str) -> SagaInstanceAggregate:
        return self._with(
            status=SagaStatus.FAILED,
            compensations=self.compensations + [{"reason": reason, "at": datetime.now(timezone.utc).isoformat()}],
        )

    def require_manual_intervention(self, reason: str) -> SagaInstanceAggregate:
        return self._with(
            status=SagaStatus.MANUAL_INTERVENTION,
            compensations=self.compensations + [{"reason": reason, "at": datetime.now(timezone.utc).isoformat()}],
        )

    def _with(self, **changes: object) -> SagaInstanceAggregate:
        data = {
            "saga_id": self.saga_id,
            "saga_type": self.saga_type,
            "tenant_id": self.tenant_id,
            "status": self.status,
            "current_step": self.current_step,
            "steps": self.steps,
            "compensations": self.compensations,
            "trace_id": self.trace_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        data.update(changes)
        data["updated_at"] = datetime.now(timezone.utc)
        return SagaInstanceAggregate(**data)  # type: ignore[arg-type]