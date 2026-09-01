"""CertificationItemExecutor 领域服务 - 注入攻击向量 + 捕获隔离行为 + 采集证据 + 判定结论。"""

from __future__ import annotations

import asyncio
from typing import Any

from app.domain.sec.attack_matrix.services.isolation_layer_executors import (
    IsolationLayerExecutor,
    LayerExecutionResult,
    get_executor,
)
from app.domain.sec.attack_matrix.value_objects.attack_vector import AttackVector
from app.domain.sec.certification.aggregates.certification_item_aggregate import (
    CertificationItemAggregate,
)
from app.domain.sec.certification.value_objects.isolation_layer import Conclusion
from app.interfaces.middleware.error_handler import SECError, SECErrorCode

_ITEM_TIMEOUT_SECONDS = 5.0


class CertificationItemExecutor:
    """认证项执行器：执行攻击向量 → 比对行为 → 采集证据 → 判定结论。"""

    def __init__(self, http_client: Any) -> None:
        self._http_client = http_client

    async def execute_item(self, item: CertificationItemAggregate) -> CertificationItemAggregate:
        if item.attack_vector is None:
            item.execute()
            item.mark_unexecutable("No attack vector attached")
            return item

        item.execute()

        executor = get_executor(item.layer)
        try:
            result: LayerExecutionResult = await asyncio.wait_for(
                executor.execute(item.attack_vector, self._http_client),
                timeout=_ITEM_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            item.judge("timeout", _ITEM_TIMEOUT_SECONDS * 1000)
            return item
        except Exception as exc:
            item.mark_unexecutable(f"Executor error: {exc}")
            return item

        if not result.is_reachable:
            item.mark_unexecutable(result.error_detail or "Module unreachable")
            return item

        if result.evidence is not None:
            item.capture_evidence(result.evidence)

        item.judge(result.actual_behavior, result.duration_ms)
        return item

    async def execute_batch(self, items: list[CertificationItemAggregate]) -> list[CertificationItemAggregate]:
        results: list[CertificationItemAggregate] = []
        for item in items:
            executed = await self.execute_item(item)
            results.append(executed)
        return results