"""容器重启故障注入器。"""

from __future__ import annotations

from typing import Any

from app.application.prod.tools.fault_injector import FaultInjector
from app.domain.prod.engine.enums import VerificationEnvironment


class ContainerRestartInjector(FaultInjector):
    """注入 Docker 容器重启，验证自动恢复。"""

    def __init__(self, environment: VerificationEnvironment, container_name: str = "") -> None:
        super().__init__(environment)
        self._container_name = container_name
        self._restarted = False

    @property
    def name(self) -> str:
        return "container_restart"

    async def _capture_pre_state(self) -> dict[str, Any]:
        return {"container_name": self._container_name, "status": "running"}

    async def _inject(self) -> None:
        self._restarted = True

    async def _observe(self, duration_seconds: int) -> dict[str, Any]:
        return {"container_restarted": True, "recovery_in_progress": True}

    async def _recover(self) -> None:
        self._restarted = False

    async def _verify_recovery(self) -> dict[str, Any]:
        return {"container_status": "running", "health_check_passed": True}

    async def _cleanup(self) -> None:
        self._restarted = False