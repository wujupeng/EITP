"""归档存储客户端 - 制品归档与检索。"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError


@dataclass(frozen=True)
class ArchiveResult:
    location: str
    content_hash: str
    size_bytes: int


class ArchiveStorageClient:
    """归档存储客户端 - 支持本地文件系统归档。"""

    def __init__(self, base_path: str) -> None:
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)

    async def archive(self, artifact_name: str, content: bytes) -> ArchiveResult:
        content_hash = hashlib.sha256(content).hexdigest()
        archive_path = self._base_path / f"{artifact_name}_{content_hash[:16]}.bin"
        archive_path.write_bytes(content)
        return ArchiveResult(
            location=str(archive_path),
            content_hash=content_hash,
            size_bytes=len(content),
        )

    async def retrieve(self, location: str) -> bytes:
        path = Path(location)
        if not path.exists():
            raise RELError(
                RELErrorCode.ASSET_SNAPSHOT_NOT_FOUND,
                f"archive not found: {location}",
            )
        return path.read_bytes()

    async def verify_hash(self, location: str, expected_hash: str) -> bool:
        content = await self.retrieve(location)
        actual_hash = hashlib.sha256(content).hexdigest()
        return actual_hash == expected_hash