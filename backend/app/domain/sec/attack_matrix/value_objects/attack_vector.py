"""AttackVector 值对象 - 攻击向量，不可变。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.domain.sec.certification.value_objects.isolation_layer import (
    IsolationLayer,
    NineOperation,
)


@dataclass(frozen=True)
class AttackVector:
    attacker_tenant_id: UUID
    target_tenant_id: UUID
    operation: NineOperation
    layer: IsolationLayer
    payload: dict[str, Any] = field(default_factory=dict)

    def inject(self) -> dict[str, Any]:
        return {
            "attacker_tenant_id": str(self.attacker_tenant_id),
            "target_tenant_id": str(self.target_tenant_id),
            "operation": self.operation.value,
            "layer": self.layer.value,
            "payload": self.payload,
        }