"""回滚方案汇编采集器 - RollbackPlanAssembler。"""

from __future__ import annotations

import hashlib
import json
from uuid import UUID

from app.application.rel.snapshot_collectors.asset_snapshot_collector import (
    AssetSnapshotCollector,
)
from app.domain.rel.aggregates.asset_snapshot_aggregate import AssetSnapshotAggregate
from app.domain.rel.aggregates.rollback_plan_aggregate import RollbackPlanAggregate
from app.domain.rel.enums import AssetType
from app.infrastructure.rel.asset_snapshot_repository import AssetSnapshotRepository
from app.infrastructure.rel.clients.archive_storage_client import ArchiveStorageClient
from app.infrastructure.rel.rollback_plan_repository import RollbackPlanRepository


class RollbackPlanAssembler(AssetSnapshotCollector):
    """回滚方案汇编采集器（5.15）。"""

    def __init__(
        self,
        snapshot_repository: AssetSnapshotRepository,
        archive_client: ArchiveStorageClient,
        rollback_repository: RollbackPlanRepository,
    ) -> None:
        super().__init__(AssetType.ROLLBACK_PLAN, snapshot_repository, archive_client)
        self._rollback_repo = rollback_repository

    async def collect(self, release_id: UUID, collected_by: str) -> AssetSnapshotAggregate:
        version_rollback_sop = {
            "steps": [
                "1. 回滚 Git Tag 至前一版本",
                "2. 回滚 Alembic 迁移（降序执行 downgrade）",
                "3. 回滚配置中心至前一 namespace 快照",
                "4. 重启服务并验证健康检查",
            ],
        }
        database_rollback_migrations = [
            {"revision": "069", "action": "downgrade"},
            {"revision": "068", "action": "downgrade"},
            {"revision": "067", "action": "downgrade"},
            {"revision": "066", "action": "downgrade"},
            {"revision": "065", "action": "downgrade"},
        ]
        config_rollback_plan = {
            "namespaces": ["REL", "PROD", "PLT", "SEC"],
            "strategy": "restore_from_snapshot",
        }

        plan_content = json.dumps({
            "version_rollback_sop": version_rollback_sop,
            "database_rollback_migrations": database_rollback_migrations,
            "config_rollback_plan": config_rollback_plan,
        }, sort_keys=True)
        plan_hash = hashlib.sha256(plan_content.encode()).hexdigest()

        plan = RollbackPlanAggregate.create(
            release_id=release_id,
            version_rollback_sop=version_rollback_sop,
            database_rollback_migrations=database_rollback_migrations,
            config_rollback_plan=config_rollback_plan,
            plan_hash=plan_hash,
        )
        await self._rollback_repo.save(plan)

        content = plan_content.encode("utf-8")
        return await self._archive_and_index(
            release_id=release_id,
            asset_name="rollback_plan",
            content=content,
            collected_by=collected_by,
        )