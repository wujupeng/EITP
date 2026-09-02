"""Docker 镜像锁定采集器 - DockerImageLockCollector。"""

from __future__ import annotations

import json
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
from app.infrastructure.rel.clients.docker_registry_client import DockerRegistryClient


class DockerImageLockCollector(AssetSnapshotCollector):
    """Docker 镜像锁定采集器（5.11）。"""

    def __init__(
        self,
        snapshot_repository: AssetSnapshotRepository,
        archive_client: ArchiveStorageClient,
        docker_client: DockerRegistryClient,
        compose_files: list[str],
    ) -> None:
        super().__init__(AssetType.DOCKER_IMAGE_LOCK, snapshot_repository, archive_client)
        self._docker_client = docker_client
        self._compose_files = compose_files

    async def collect(self, release_id: UUID, collected_by: str) -> AssetSnapshotAggregate:
        all_images = []
        for compose_file in self._compose_files:
            images = await self._docker_client.scan_compose_images(compose_file)
            for img in images:
                if not img.is_locked:
                    raise RELError(
                        RELErrorCode.IMAGE_FLOATING_TAG,
                        f"image {img.name}:{img.tag} uses floating tag",
                    )
                if img.digest is None:
                    raise RELError(
                        RELErrorCode.IMAGE_NOT_LOCKED,
                        f"image {img.name}:{img.tag} has no digest",
                    )
                all_images.append({
                    "name": img.name,
                    "tag": img.tag,
                    "digest": img.digest,
                })

        content = json.dumps(all_images, sort_keys=True).encode("utf-8")
        return await self._archive_and_index(
            release_id=release_id,
            asset_name="docker_image_lock",
            content=content,
            collected_by=collected_by,
        )