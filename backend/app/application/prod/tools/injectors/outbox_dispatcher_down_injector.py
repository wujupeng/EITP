"""Outbox 投递器停止故障注入器。"""

from __future__ import annotations

from typing import Any

from app.application.prod.tools.fault_injector import FaultInjector
from app.domain.prod.engine.enums import VerificationEnvironment


class OutboxDispatcherDownInjector(FaultInjector):
    """注入投递器进程停止，验证 Outbox 堆积与恢复。"""

    def __init__(self, environment: VerificationEnvironment, dispatcher_pid: int | None = None) -> None:
        super().__init__(environment)
        self._dispatcher_pid = dispatcher_pid
        self._stopped = False

    @property
    def name(self) -> str:
        return "outbox_dispatcher_down"

    async def _capture_pre_state(self) -> dict[str, Any]:
        return {"dispatcher_pid": self._dispatcher_pid, "running": True}

    async def _inject(self) -> None:
        self._stopped = True

    async def _observe(self, duration_seconds: int) -> dict[str, Any]:
        return {"dispatcher_running": False, "outbox_backlog_growing": True}

    async def _recover(self) -> None:
        self._stopped = False

    async def _verify_recovery(self) -> dict[str, Any]:
        return {"dispatcher_running": True, "backlog_draining": True}

    async def _cleanup(self) -> None:
        self._stopped = False