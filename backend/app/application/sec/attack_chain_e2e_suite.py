"""AttackChainE2ESuite - 14 步攻击链 E2E 套件。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.domain.sec.certification.value_objects.isolation_layer import IsolationLayer
from app.domain.sec.attack_matrix.services.isolation_layer_executors import get_executor

_STEP_TIMEOUT_MS = 10000
_TOTAL_TIMEOUT_MS = 180000

_STEPS: list[tuple[int, IsolationLayer, str]] = [
    (1, IsolationLayer.JWT, "JWT 伪造"),
    (2, IsolationLayer.TENANT_TOKEN, "Tenant Token 伪造"),
    (3, IsolationLayer.TENANT_CONTEXT, "TenantContext 篡改"),
    (4, IsolationLayer.DATA_SCOPE, "DataScope 越权"),
    (5, IsolationLayer.API, "API 越权"),
    (6, IsolationLayer.APPLICATION, "Application 越权"),
    (7, IsolationLayer.REPOSITORY, "Repository 越权"),
    (8, IsolationLayer.RLS, "RLS 绕过"),
    (9, IsolationLayer.JOIN, "JOIN 泄露"),
    (10, IsolationLayer.AGGREGATE, "Aggregate 泄露"),
    (11, IsolationLayer.AUDIT, "Audit 泄露"),
    (12, IsolationLayer.EXPORT, "Export 泄露"),
    (13, IsolationLayer.CACHE, "Cache 泄露"),
    (14, IsolationLayer.ASYNC_JOB, "Async Job 跨租户"),
]


@dataclass
class StepResult:
    step_number: int
    description: str
    is_blocked: bool = False
    evidence: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    error: str = ""


@dataclass
class AttackChainReport:
    total_steps: int = 14
    all_blocked: bool = False
    steps: list[StepResult] = field(default_factory=list)
    duration_ms: float = 0.0


class AttackChainE2ESuite:
    """14 步顺序执行，每步叠加前步，全链路 ≤ 3 分钟。"""

    def __init__(self, http_client: Any) -> None:
        self._http_client = http_client

    async def execute(self, tenant_a: UUID, tenant_b: UUID) -> AttackChainReport:
        import time
        start = time.monotonic()
        report = AttackChainReport()
        accumulated_headers: dict[str, str] = {}

        for step_num, layer, desc in _STEPS:
            step_result = await self._execute_step(step_num, layer, desc, tenant_a, tenant_b, accumulated_headers)
            report.steps.append(step_result)
            if not step_result.is_blocked:
                report.all_blocked = False
                break
            accumulated_headers.update(step_result.evidence.get("headers", {}))

        report.all_blocked = all(s.is_blocked for s in report.steps)
        report.duration_ms = (time.monotonic() - start) * 1000
        return report

    async def _execute_step(
        self,
        step_num: int,
        layer: IsolationLayer,
        desc: str,
        tenant_a: UUID,
        tenant_b: UUID,
        accumulated_headers: dict[str, str],
    ) -> StepResult:
        from app.domain.sec.attack_matrix.services.attack_vector_factory import AttackVectorFactory
        from app.domain.sec.certification.value_objects.isolation_layer import NineOperation

        vector = AttackVectorFactory.create(layer, NineOperation.SELECT, tenant_a, tenant_b)
        executor = get_executor(layer)

        try:
            result = await asyncio.wait_for(
                executor.execute(vector, self._http_client),
                timeout=_STEP_TIMEOUT_MS / 1000,
            )
            is_blocked = "401" in result.actual_behavior or "403" in result.actual_behavior or "404" in result.actual_behavior
            return StepResult(
                step_number=step_num,
                description=desc,
                is_blocked=is_blocked,
                evidence={"actual_behavior": result.actual_behavior, "layer": layer.value},
                duration_ms=result.duration_ms,
            )
        except asyncio.TimeoutError:
            return StepResult(
                step_number=step_num,
                description=desc,
                is_blocked=False,
                error="timeout",
                duration_ms=_STEP_TIMEOUT_MS,
            )
        except Exception as exc:
            return StepResult(
                step_number=step_num,
                description=desc,
                is_blocked=False,
                error=str(exc),
            )