"""门禁校验器基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from app.domain.rel.enums import GateType


@dataclass(frozen=True)
class GateResult:
    gate_type: GateType
    passed: bool
    detail: dict
    error_code: str | None = None
    error_message: str | None = None


class GateChecker(ABC):
    """门禁校验器抽象基类。"""

    @property
    @abstractmethod
    def gate_type(self) -> GateType: ...

    @abstractmethod
    async def check(self, release_id: UUID, executed_by: str) -> GateResult: ...