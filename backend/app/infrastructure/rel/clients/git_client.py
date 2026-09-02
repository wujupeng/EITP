"""Git CLI 客户端 - 封装 Git 操作。"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError


@dataclass(frozen=True)
class WorktreeStatus:
    is_clean: bool
    dirty_files: list[str]


class GitClient:
    """Git CLI 异步客户端。"""

    def __init__(self, repo_path: str, remote: str = "origin") -> None:
        self._repo_path = repo_path
        self._remote = remote

    async def _run_git(self, *args: str) -> str:
        proc = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=self._repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RELError(
                RELErrorCode.TAG_PUSH_FAILED,
                f"git {args[0]} failed: {stderr.decode().strip()}",
            )
        return stdout.decode().strip()

    async def create_annotated_tag(self, tag: str, message: str) -> None:
        await self._run_git("tag", "-a", tag, "-m", message)

    async def push_tag(self, tag: str) -> None:
        await self._run_git("push", self._remote, tag)

    async def get_commit_sha(self, tag: str) -> str:
        return await self._run_git("rev-parse", f"{tag}^{{commit}}")

    async def check_worktree_clean(self) -> WorktreeStatus:
        output = await self._run_git("status", "--porcelain")
        if not output:
            return WorktreeStatus(is_clean=True, dirty_files=[])
        files = [line.split(maxsplit=1)[1] for line in output.strip().split("\n")]
        return WorktreeStatus(is_clean=False, dirty_files=files)

    async def check_tag_exists(self, tag: str) -> bool:
        proc = await asyncio.create_subprocess_exec(
            "git",
            "tag",
            "-l",
            tag,
            cwd=self._repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return bool(stdout.decode().strip())

    async def verify_annotated_tag(self, tag: str) -> bool:
        proc = await asyncio.create_subprocess_exec(
            "git",
            "for-each-ref",
            f"refs/tags/{tag}",
            "--format=%(objecttype)",
            cwd=self._repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode().strip() == "tag"

    async def register_server_side_hook(self, hook_script_path: str) -> None:
        await self._run_git("config", "core.hooksPath", ".githooks")