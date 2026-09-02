"""Git Tag 冲突校验器。"""

from __future__ import annotations

from uuid import UUID

from app.application.rel.gate_checkers.base_checker import GateChecker, GateResult
from app.domain.rel.enums import GateType
from app.domain.rel.error_codes import RELErrorCode
from app.infrastructure.rel.clients.git_client import GitClient


class GitTagConflictChecker(GateChecker):
    """检测 Git Tag 是否已存在。"""

    def __init__(self, git_client: GitClient, tag_name: str) -> None:
        self._git_client = git_client
        self._tag_name = tag_name

    @property
    def gate_type(self) -> GateType:
        return GateType.TAG_CONFLICT

    async def check(self, release_id: UUID, executed_by: str) -> GateResult:
        exists = await self._git_client.check_tag_exists(self._tag_name)
        if exists:
            return GateResult(
                gate_type=self.gate_type,
                passed=False,
                detail={"tag": self._tag_name, "exists": True},
                error_code=RELErrorCode.GATE_TAG_EXISTS.value,
                error_message=f"tag {self._tag_name} already exists",
            )
        return GateResult(
            gate_type=self.gate_type,
            passed=True,
            detail={"tag": self._tag_name, "exists": False},
        )