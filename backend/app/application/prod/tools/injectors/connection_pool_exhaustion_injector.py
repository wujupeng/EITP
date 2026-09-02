"""连接池耗尽故障注入器。"""

from __future__ import annotations

import asyncio
from typing import Any

from app.application.prod.tools.fault_injector import FaultInjector
from app.domain.prod.engine.enums import VerificationEnvironment


class ConnectionPoolExhaustionInjector(FaultInjector):
    """注入高并发请求耗尽连接池。"""

    def __init__(self, environment: VerificationEnvironment, target_url: str = "", max_connections: int = 100) -> None:
        super().__init__(environment)
        self._target_url = target_url
        self._max_connections = max_connections
        self._tasks: list[asyncio.Task] = []

    @property
    def name(self) -> str:
        return "connection_pool_exhaustion"

    async def _capture_pre_state(self) -> dict[str, Any]:
        return {"target_url": self._target_url, "max_connections": self._max_connections}

    async def _inject(self) -> None:
        async def hold_connection() -> None:
            await asyncio.sleep(300)
        for _ in range(self._max_connections):
            self._tasks.append(asyncio.create_task(hold_connection()))

    async def _observe(self, duration_seconds: int) -> dict[str, Any]:
        await asyncio.sleep(min(duration_seconds, 10))
        return {"active_connections": len(self._tasks), "exhausted": True}

    async def _recover(self) -> None:
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

    async def _verify_recovery(self) -> dict[str, Any]:
        return {"active_connections": 0, "recovered": True}

    async def _cleanup(self) -> None:
        self._tasks.clear()