"""ArchiveStorageClient 单元测试 - 归档/检索/哈希校验。

覆盖 infrastructure/rel/clients/archive_storage_client.py 的 archive/retrieve/verify_hash：
- archive 写入文件并返回 sha256 哈希/位置/大小
- retrieve 读取已归档内容
- retrieve 不存在位置抛 RELError
- verify_hash 一致/不一致
- 相同内容产生相同哈希
"""

from __future__ import annotations

import hashlib

import pytest

from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError
from app.infrastructure.rel.clients.archive_storage_client import ArchiveStorageClient


class ArchiveStorageClientTest:
    """ArchiveStorageClient 归档存储客户端测试。"""

    async def test_archive_writes_file_and_returns_result(self, tmp_path) -> None:
        client = ArchiveStorageClient(base_path=str(tmp_path))
        content = b"release artifact"
        result = await client.archive("artifact_1", content)
        expected_hash = hashlib.sha256(content).hexdigest()
        assert result.content_hash == expected_hash
        assert result.size_bytes == len(content)
        assert "artifact_1" in result.location
        assert expected_hash[:16] in result.location

    async def test_archive_content_retrievable(self, tmp_path) -> None:
        client = ArchiveStorageClient(base_path=str(tmp_path))
        content = b"some bytes"
        result = await client.archive("a2", content)
        retrieved = await client.retrieve(result.location)
        assert retrieved == content

    async def test_archive_same_content_produces_same_hash(self, tmp_path) -> None:
        client = ArchiveStorageClient(base_path=str(tmp_path))
        r1 = await client.archive("x", b"identical")
        r2 = await client.archive("y", b"identical")
        assert r1.content_hash == r2.content_hash

    async def test_archive_different_content_produces_different_hash(self, tmp_path) -> None:
        client = ArchiveStorageClient(base_path=str(tmp_path))
        r1 = await client.archive("x", b"aaa")
        r2 = await client.archive("y", b"bbb")
        assert r1.content_hash != r2.content_hash

    async def test_retrieve_nonexistent_location_raises(self, tmp_path) -> None:
        client = ArchiveStorageClient(base_path=str(tmp_path))
        with pytest.raises(RELError) as exc:
            await client.retrieve(str(tmp_path / "missing.bin"))
        assert exc.value.code == RELErrorCode.ASSET_SNAPSHOT_NOT_FOUND

    async def test_verify_hash_match_returns_true(self, tmp_path) -> None:
        client = ArchiveStorageClient(base_path=str(tmp_path))
        result = await client.archive("v", b"verify me")
        ok = await client.verify_hash(result.location, result.content_hash)
        assert ok is True

    async def test_verify_hash_mismatch_returns_false(self, tmp_path) -> None:
        client = ArchiveStorageClient(base_path=str(tmp_path))
        result = await client.archive("v", b"verify me")
        ok = await client.verify_hash(result.location, "0" * 64)
        assert ok is False

    async def test_archive_size_bytes_matches_content_length(self, tmp_path) -> None:
        client = ArchiveStorageClient(base_path=str(tmp_path))
        content = b"x" * 4096
        result = await client.archive("sized", content)
        assert result.size_bytes == 4096

    async def test_base_path_created_if_not_exists(self, tmp_path) -> None:
        base = tmp_path / "nested" / "archive"
        client = ArchiveStorageClient(base_path=str(base))
        assert base.exists()
        result = await client.archive("k", b"data")
        assert result.content_hash == hashlib.sha256(b"data").hexdigest()