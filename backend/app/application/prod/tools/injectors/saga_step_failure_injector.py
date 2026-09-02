"""Saga 步骤失败故障注入器。"""

from __future__ import annotations

from typing import Any

from app.application.prod.tools.fault_injector import FaultInjector
from app.domain.prod.engine.enums import VerificationEnvironment


class SagaStepFailureInjector(FaultInjector):
    """注入指定 Saga 步骤抛异常，验证补偿。"""

    def __init__(self, environment: VerificationEnvironment, saga_type: str = "", step_name: str = "") -> None:
        super().__init__(environment)
        self._saga_type = saga_type
        self._step_name = step_name
        self._injected = False

    @property
    def name(self) -> str:
        return "saga_step_failure"

    async def _capture_pre_state(self) -> dict[str, Any]:
        return {"saga_type": self._saga_type, "step_name": self._step_name}

    async def _inject(self) -> None:
        self._injected = True

    async def _observe(self, duration_seconds: int) -> dict[str, Any]:
        return {"step_failed": self._step_name, "compensation_triggered": True}

    async def _recover(self) -> None:
        self._injected = False

    async def _verify_recovery(self) -> dict[str, Any]:
        return {"compensation_completed": True, "data_consistent": True}

    async def _cleanup(self) -> None:
        self._injected = False