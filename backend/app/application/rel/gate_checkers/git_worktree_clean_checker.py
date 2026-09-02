"""Git 工作区干净校验器。"""

from __future__ import annotations

from uuid import UUID

from app.application.rel.gate_checkers.base_checker import GateChecker, GateResult
from app.domain.rel.enums import GateType
from app.domain.rel.error_codes import RELErrorCode
from app.infrastructure.rel.clients.git_client import GitClient


class GitWorktreeCleanChecker(GateChecker):
    """检测 Git 工作区是否有未提交变更。"""

    def __init__(self, git_client: GitClient) -> None:
        self._git_client = git_client

    @property
    def gate_type(self) -> GateType:
        return GateType.GIT_CLEAN

    async def check(self, release_id: UUID, executed_by: str) -> GateResult:
        status = await self._git_client.check_worktree_clean()
        if not status.is_clean:
            return GateResult(
                gate_type=self.gate_type,
                passed=False,
                detail={"dirty_files": status.dirty_files},
                error_code=RELErrorCode.GATE_DIRTY_WORKTREE.value,
                error_message=f"{len(status.dirty_files)} uncommitted file(s)",
            )
        return GateResult(
            gate_type=self.gate_type,
            passed=True,
            detail={"clean": True},
        )