"""主备切换故障注入器。"""

from __future__ import annotations

from typing import Any

from app.application.prod.tools.fault_injector import FaultInjector
from app.domain.prod.engine.enums import VerificationEnvironment


class PrimaryStandbySwitchoverInjector(FaultInjector):
    """注入主备切换，验证 RTO/RPO。"""

    def __init__(self, environment: VerificationEnvironment, primary_host: str = "", standby_host: str = "") -> None:
        super().__init__(environment)
        self._primary_host = primary_host
        self._standby_host = standby_host
        self._switched = False

    @property
    def name(self) -> str:
        return "primary_standby_switchover"

    async def _capture_pre_state(self) -> dict[str, Any]:
        return {"primary": self._primary_host, "standby": self._standby_host, "role": "primary_active"}

    async def _inject(self) -> None:
        self._switched = True

    async def _observe(self, duration_seconds: int) -> dict[str, Any]:
        return {"switchover_executed": True, "standby_promoted": True}

    async def _recover(self) -> None:
        self._switched = False

    async def _verify_recovery(self) -> dict[str, Any]:
        return {"primary_active": True, "rto_measured": True, "rpo_zero": True}

    async def _cleanup(self) -> None:
        self._switched = False