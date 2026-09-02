"""Saga 编排器 - 分布式事务编排与补偿。"""

from __future__ import annotations

from typing import Any, Callable
from uuid import UUID

from structlog import get_logger

from app.domain.platform.consistency.aggregates.saga_instance_aggregate import (
    SagaInstanceAggregate,
    SagaStatus,
)
from app.domain.platform.error_codes import PLTErrorCode
from app.domain.platform.exceptions import PLTError

logger = get_logger(__name__)


class SagaOrchestrator:
    """Saga 编排器 - 执行步骤序列，失败时自动补偿。"""

    def __init__(self, repository: Any) -> None:
        self._repository = repository
        self._step_handlers: dict[str, Callable] = {}
        self._compensation_handlers: dict[str, Callable] = {}

    def register_step(self, step_name: str, handler: Callable) -> None:
        self._step_handlers[step_name] = handler

    def register_compensation(self, step_name: str, handler: Callable) -> None:
        self._compensation_handlers[step_name] = handler

    async def execute(self, saga: SagaInstanceAggregate) -> SagaInstanceAggregate:
        await self._repository.save(saga)
        current = saga

        for i, step in enumerate(saga.steps):
            step_name = step.get("name", f"step_{i}")
            handler = self._step_handlers.get(step_name)
            if handler is None:
                current = current.require_manual_intervention(f"未注册步骤处理器: {step_name}")
                await self._repository.save(current)
                raise PLTError(PLTErrorCode.SAGA_STEP_FAILED, f"未注册步骤处理器: {step_name}")

            try:
                await handler(step.get("params", {}), current)
                current = current.advance_step()
                await self._repository.save(current)
                logger.info("saga_step_completed", saga_id=str(current.saga_id), step=step_name)
            except Exception as exc:
                logger.error("saga_step_failed", saga_id=str(current.saga_id), step=step_name, error=str(exc))
                current = current.start_compensation()
                await self._repository.save(current)
                current = await self._compensate(current)
                await self._repository.save(current)
                return current

        return current

    async def _compensate(self, saga: SagaInstanceAggregate) -> SagaInstanceAggregate:
        current = saga
        for i in range(saga.current_step - 1, -1, -1):
            step = saga.steps[i] if i < len(saga.steps) else {}
            step_name = step.get("name", f"step_{i}")
            comp_handler = self._compensation_handlers.get(step_name)

            if comp_handler is not None:
                try:
                    await comp_handler(step.get("params", {}), current)
                    logger.info("saga_compensation_completed", saga_id=str(current.saga_id), step=step_name)
                except Exception as exc:
                    logger.error("saga_compensation_failed", saga_id=str(current.saga_id), step=step_name, error=str(exc))
                    current = current.require_manual_intervention(f"补偿失败: {step_name}")
                    return current

        current = current.complete_compensation()
        return current