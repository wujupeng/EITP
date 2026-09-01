"""AttackChainStepExecutor - 攻击链单步执行器。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domain.sec.attack_matrix.value_objects.attack_vector import AttackVector
from app.domain.sec.attack_matrix.services.isolation_layer_executors import get_executor
from app.domain.sec.certification.value_objects.isolation_layer import IsolationLayer


@dataclass
class StepExecutionResult:
    step_number: int
    is_blocked: bool = False
    actual_behavior: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0


class AttackChainStepExecutor:
    """执行单步攻击，捕获隔离行为，记录证据快照。"""

    def __init__(self, http_client: Any) -> None:
        self._http_client = http_client

    async def execute_step(
        self,
        step_number: int,
        layer: IsolationLayer,
        vector: AttackVector,
    ) -> StepExecutionResult:
        executor = get_executor(layer)
        result = await executor.execute(vector, self._http_client)
        is_blocked = any(code in result.actual_behavior for code in ("401", "403", "404"))
        return StepExecutionResult(
            step_number=step_number,
            is_blocked=is_blocked,
            actual_behavior=result.actual_behavior,
            evidence=result.evidence.__dict__ if result.evidence else {},
            duration_ms=result.duration_ms,
        )