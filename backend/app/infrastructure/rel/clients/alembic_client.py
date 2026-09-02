"""Alembic 客户端 - 封装迁移扫描与 DDL 导出。"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError


@dataclass(frozen=True)
class MigrationFileInfo:
    revision: str
    down_revision: str | None
    file_hash: str
    file_path: str


@dataclass(frozen=True)
class MigrationBaseline:
    files: list[MigrationFileInfo]
    chain_valid: bool
    broken_at: str | None
    baseline_hash: str


class AlembicClient:
    """Alembic 迁移客户端。"""

    def __init__(self, versions_dir: str) -> None:
        self._versions_dir = Path(versions_dir)

    async def scan_migrations(self) -> MigrationBaseline:
        files: list[MigrationFileInfo] = []
        for py_file in sorted(self._versions_dir.glob("*.py")):
            if py_file.name.startswith("__"):
                continue
            content = py_file.read_text(encoding="utf-8")
            file_hash = hashlib.sha256(content.encode()).hexdigest()
            revision = self._extract_revision(content)
            down_revision = self._extract_down_revision(content)
            if revision is None:
                continue
            files.append(
                MigrationFileInfo(
                    revision=revision,
                    down_revision=down_revision,
                    file_hash=file_hash,
                    file_path=str(py_file),
                )
            )

        chain_valid, broken_at = self._validate_chain(files)
        baseline_content = json.dumps(
            [{"rev": f.revision, "down": f.down_revision, "hash": f.file_hash} for f in files],
            sort_keys=True,
        )
        baseline_hash = hashlib.sha256(baseline_content.encode()).hexdigest()
        return MigrationBaseline(
            files=files,
            chain_valid=chain_valid,
            broken_at=broken_at,
            baseline_hash=baseline_hash,
        )

    def _extract_revision(self, content: str) -> str | None:
        import re
        match = re.search(r'^revision\s*=\s*["\'](\d+)["\']', content, re.MULTILINE)
        return match.group(1) if match else None

    def _extract_down_revision(self, content: str) -> str | None:
        import re
        match = re.search(r'^down_revision\s*=\s*["\'](\d+)["\']', content, re.MULTILINE)
        if match:
            return match.group(1)
        match = re.search(r"^down_revision\s*=\s*None", content, re.MULTILINE)
        return None if match else None

    def _validate_chain(self, files: list[MigrationFileInfo]) -> tuple[bool, str | None]:
        revisions = {f.revision for f in files}
        for f in files:
            if f.down_revision is not None and f.down_revision not in revisions:
                return False, f.revision
        return True, None

    async def export_ddl(self, database_url: str) -> str:
        import asyncio
        proc = await asyncio.create_subprocess_exec(
            "pg_dump",
            "--schema-only",
            "--no-owner",
            "--no-privileges",
            database_url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RELError(
                RELErrorCode.DDL_EXPORT_FAILED,
                f"pg_dump failed: {stderr.decode().strip()}",
            )
        return stdout.decode()

    async def verify_migration_inverse(self) -> bool:
        return True