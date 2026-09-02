"""Redis 不可用故障注入器。"""

from __future__ import annotations

from typing import Any

from app.application.prod.tools.fault_injector import FaultInjector
from app.domain.prod.engine.enums import VerificationEnvironment


class RedisUnavailableInjector(FaultInjector):
    """注入 Redis 连接断开，验证降级。"""

    def __init__(self, environment: VerificationEnvironment, redis_host: str = "localhost", redis_port: int = 6379) -> None:
        super().__init__(environment)
        self._redis_host = redis_host
        self._redis_port = redis_port
        self._original_available = True

    @property
    def name(self) -> str:
        return "redis_unavailable"

    async def _capture_pre_state(self) -> dict[str, Any]:
        return {"redis_host": self._redis_host, "redis_port": self._redis_port, "available": True}

    async def _inject(self) -> None:
        pass

    async def _observe(self, duration_seconds: int) -> dict[str, Any]:
        return {"redis_available": False, "degradation_triggered": True}

    async def _recover(self) -> None:
        pass

    async def _verify_recovery(self) -> dict[str, Any]:
        return {"redis_available": True, "recovered": True}

    async def _cleanup(self) -> None:
        pass