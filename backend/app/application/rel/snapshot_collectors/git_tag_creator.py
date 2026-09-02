"""Git Tag 代码快照固化采集器 - GitTagCreator。"""

from __future__ import annotations

from uuid import UUID

from app.application.rel.snapshot_collectors.asset_snapshot_collector import (
    AssetSnapshotCollector,
)
from app.domain.rel.aggregates.asset_snapshot_aggregate import AssetSnapshotAggregate
from app.domain.rel.enums import AssetType
from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError
from app.infrastructure.rel.asset_snapshot_repository import AssetSnapshotRepository
from app.infrastructure.rel.clients.archive_storage_client import ArchiveStorageClient
from app.infrastructure.rel.clients.git_client import GitClient


class GitTagCreator(AssetSnapshotCollector):
    """Git Tag 代码快照固化采集器（5.2）。"""

    def __init__(
        self,
        snapshot_repository: AssetSnapshotRepository,
        archive_client: ArchiveStorageClient,
        git_client: GitClient,
        tag_name: str = "v1.0.0",
    ) -> None:
        super().__init__(AssetType.GIT_TAG, snapshot_repository, archive_client)
        self._git_client = git_client
        self._tag_name = tag_name

    async def collect(self, release_id: UUID, collected_by: str) -> AssetSnapshotAggregate:
        tag_message = f"EITP Release {self._tag_name} | sealed by {collected_by} | release_id={release_id}"
        await self._git_client.create_annotated_tag(self._tag_name, tag_message)

        is_annotated = await self._git_client.verify_annotated_tag(self._tag_name)
        if not is_annotated:
            raise RELError(
                RELErrorCode.TAG_NOT_ANNOTATED,
                f"tag {self._tag_name} is not an annotated tag",
            )

        await self._git_client.push_tag(self._tag_name)

        await self._git_client.register_server_side_hook(".githooks/pre-receive")

        commit_sha = await self._git_client.get_commit_sha(self._tag_name)

        content = commit_sha.encode("utf-8")
        snapshot = await self._archive_and_index(
            release_id=release_id,
            asset_name=f"git_tag_{self._tag_name}",
            content=content,
            collected_by=collected_by,
        )

        logger_msg = f"git_tag_created: {self._tag_name} commit={commit_sha}"
        return snapshot