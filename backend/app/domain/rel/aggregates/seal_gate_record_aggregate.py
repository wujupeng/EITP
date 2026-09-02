"""REL 封版门禁记录聚合根 - SealGateRecordAggregate。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.rel.enums import GateType


@dataclass(frozen=True)
class SealGateRecordAggregate:
    """门禁记录聚合根 - append-only 不可变。"""

    gate_id: UUID
    release_id: UUID
    gate_type: GateType
    gate_result: str
    gate_detail: dict
    gate_time: datetime
    executed_by: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        release_id: UUID,
        gate_type: GateType,
        gate_result: str,
        gate_detail: dict,
        executed_by: str,
    ) -> SealGateRecordAggregate:
        return cls(
            gate_id=uuid4(),
            release_id=release_id,
            gate_type=gate_type,
            gate_result=gate_result,
            gate_detail=gate_detail,
            gate_time=datetime.now(timezone.utc),
            executed_by=executed_by,
        )