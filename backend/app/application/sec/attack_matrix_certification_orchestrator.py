"""AttackMatrixCertificationOrchestrator - 15 层攻击矩阵认证编排器。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.domain.sec.attack_matrix.aggregates.attack_matrix_definition import AttackMatrixDefinition
from app.domain.sec.attack_matrix.services.attack_vector_factory import AttackVectorFactory
from app.domain.sec.attack_matrix.services.certification_item_executor import CertificationItemExecutor
from app.domain.sec.certification.aggregates.certification_batch_aggregate import CertificationBatchAggregate
from app.domain.sec.certification.aggregates.certification_item_aggregate import CertificationItemAggregate
from app.domain.sec.certification.value_objects.batch_status import BatchStatus
from app.domain.sec.certification.value_objects.isolation_layer import (
    Conclusion,
    IsolationLayer,
    NineOperation,
)
from app.domain.sec.attack_matrix.value_objects.attack_vector import AttackVector
from app.infrastructure.sec.test_tenant_provisioner import TestTenantProvisioner, TestTenantPair

_PARALLELISM = 4


@dataclass
class MatrixExecutionProgress:
    batch_id: UUID
    status: BatchStatus
    total_items: int = 0
    passed: int = 0
    failed: int = 0
    unexecutable: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total_items if self.total_items > 0 else 0.0


@dataclass
class MatrixExecutionResult:
    batch_id: UUID
    progress: MatrixExecutionProgress
    items: list[CertificationItemAggregate] = field(default_factory=list)


class AttackMatrixCertificationOrchestrator:
    """编排 15 层攻击矩阵认证执行，层间并行(4) + 层内串行。"""

    def __init__(self, http_client: Any) -> None:
        self._http_client = http_client
        self._item_executor = CertificationItemExecutor(http_client)
        self._provisioner = TestTenantProvisioner(http_client)
        self._progress: dict[UUID, MatrixExecutionProgress] = {}

    async def execute(
        self,
        matrix_version: str,
        tenant_id: UUID,
        trigger_source: str = "manual",
        layers: list[IsolationLayer] | None = None,
    ) -> MatrixExecutionResult:
        batch = CertificationBatchAggregate(
            batch_id=uuid4(),
            matrix_version=matrix_version,
            trigger_source=trigger_source,
            tenant_id=tenant_id,
        )
        batch.start()
        progress = MatrixExecutionProgress(batch_id=batch.batch_id, status=batch.status, started_at=batch.started_at)
        self._progress[batch.batch_id] = progress

        pair = await self._provisioner.provision(prefix=f"sec-{matrix_version}")

        try:
            target_layers = layers or list(IsolationLayer)
            matrix_def = AttackMatrixDefinition()
            all_items = matrix_def.generate_items(batch.batch_id, pair.tenant_a, target_layers)
            progress.total_items = len(all_items)

            layer_groups: dict[IsolationLayer, list[CertificationItemAggregate]] = {}
            for item in all_items:
                layer_groups.setdefault(item.layer, []).append(item)

            sem = asyncio.Semaphore(_PARALLELISM)

            async def run_layer(layer: IsolationLayer, items: list[CertificationItemAggregate]) -> list[CertificationItemAggregate]:
                async with sem:
                    return await self._item_executor.execute_batch(items)

            layer_results = await asyncio.gather(
                *(run_layer(layer, items) for layer, items in layer_groups.items()),
                return_exceptions=False,
            )

            all_executed: list[CertificationItemAggregate] = []
            for result in layer_results:
                all_executed.extend(result)

            passed = sum(1 for i in all_executed if i.conclusion == Conclusion.PASS)
            failed = sum(1 for i in all_executed if i.conclusion == Conclusion.FAIL)
            unexecutable = sum(1 for i in all_executed if i.conclusion == Conclusion.UNEXECUTABLE)

            batch.complete(passed, failed, unexecutable)
            progress.status = batch.status
            progress.passed = passed
            progress.failed = failed
            progress.unexecutable = unexecutable
            progress.completed_at = batch.completed_at

            result = MatrixExecutionResult(batch_id=batch.batch_id, progress=progress, items=all_executed)

        except Exception as exc:
            batch.fail(str(exc))
            progress.status = batch.status
            progress.completed_at = batch.completed_at
            result = MatrixExecutionResult(batch_id=batch.batch_id, progress=progress)
        finally:
            await self._provisioner.cleanup(pair)

        return result

    def get_progress(self, batch_id: UUID) -> MatrixExecutionProgress | None:
        return self._progress.get(batch_id)