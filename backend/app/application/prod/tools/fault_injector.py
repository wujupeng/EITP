"""故障注入器基类 - 校验环境、注入故障、观测、恢复、清理。"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.domain.audit.audit_entry import AuditAction, AuditEntry
from app.domain.prod.engine.enums import VerificationEnvironment
from app.domain.prod.error_codes import PRODErrorCode
from app.domain.prod.exceptions import PRODError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FaultInjectionResult:
    """故障注入结果。"""

    injector_name: str
    started_at: datetime
    recovered_at: datetime
    pre_state: dict[str, Any]
    post_state: dict[str, Any]
    observations: dict[str, Any]
    success: bool
    error: str | None = None


class FaultInjector(ABC):
    """故障注入器基类。

    流程: 校验环境 → 记录故障前状态 → 注入故障 → 观测 → 恢复 → 校验恢复 → 清理
    """

    def __init__(self, environment: VerificationEnvironment) -> None:
        if environment == VerificationEnvironment.STAGING or environment == VerificationEnvironment.PRE_PROD:
            self._environment = environment
        else:
            raise PRODError(
                PRODErrorCode.VERIFICATION_ENV_FORBIDDEN,
                f"故障注入器禁止在 {environment} 环境执行",
            )

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def _capture_pre_state(self) -> dict[str, Any]: ...

    @abstractmethod
    async def _inject(self) -> None: ...

    @abstractmethod
    async def _observe(self, duration_seconds: int) -> dict[str, Any]: ...

    @abstractmethod
    async def _recover(self) -> None: ...

    @abstractmethod
    async def _verify_recovery(self) -> dict[str, Any]: ...

    @abstractmethod
    async def _cleanup(self) -> None: ...

    async def execute(
        self,
        duration_seconds: int = 30,
        tenant_id: UUID | None = None,
    ) -> FaultInjectionResult:
        started_at = datetime.now(timezone.utc)
        logger.info("Fault injection [%s] starting in %s", self.name, self._environment.value)

        pre_state = await self._capture_pre_state()

        try:
            await self._inject()
            observations = await self._observe(duration_seconds)
            await self._recover()
            post_state = await self._verify_recovery()
            await self._cleanup()

            recovered_at = datetime.now(timezone.utc)
            result = FaultInjectionResult(
                injector_name=self.name,
                started_at=started_at,
                recovered_at=recovered_at,
                pre_state=pre_state,
                post_state=post_state,
                observations=observations,
                success=True,
            )
            logger.info("Fault injection [%s] completed successfully", self.name)
            return result

        except Exception as exc:
            recovered_at = datetime.now(timezone.utc)
            logger.error("Fault injection [%s] failed: %s", self.name, exc)
            try:
                await self._recover()
                await self._cleanup()
            except Exception:
                pass
            return FaultInjectionResult(
                injector_name=self.name,
                started_at=started_at,
                recovered_at=recovered_at,
                pre_state=pre_state,
                post_state={},
                observations={},
                success=False,
                error=str(exc),
            )