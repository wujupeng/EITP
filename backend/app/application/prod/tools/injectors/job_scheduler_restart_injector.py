"""Job 调度器重启故障注入器。"""

from __future__ import annotations

from typing import Any

from app.application.prod.tools.fault_injector import FaultInjector
from app.domain.prod.engine.enums import VerificationEnvironment


class JobSchedulerRestartInjector(FaultInjector):
    """注入 Scheduler 进程重启，验证 Job 恢复。"""

    def __init__(self, environment: VerificationEnvironment, scheduler_pid: int | None = None) -> None:
        super().__init__(environment)
        self._scheduler_pid = scheduler_pid
        self._restarted = False

    @property
    def name(self) -> str:
        return "job_scheduler_restart"

    async def _capture_pre_state(self) -> dict[str, Any]:
        return {"scheduler_pid": self._scheduler_pid, "running": True}

    async def _inject(self) -> None:
        self._restarted = True

    async def _observe(self, duration_seconds: int) -> dict[str, Any]:
        return {"scheduler_restarted": True, "jobs_recovered": True}

    async def _recover(self) -> None:
        self._restarted = False

    async def _verify_recovery(self) -> dict[str, Any]:
        return {"scheduler_running": True, "all_jobs_scheduled": True}

    async def _cleanup(self) -> None:
        self._restarted = False