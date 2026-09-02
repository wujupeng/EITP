"""REL 回滚方案仓储 - 仅演练状态字段可更新。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.rel.aggregates.rollback_plan_aggregate import RollbackPlanAggregate


class RollbackPlanRepository:
    """回滚方案仓储。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, plan: RollbackPlanAggregate) -> None:
        await self._session.execute(
            text(
                "INSERT INTO rel_rollback_plan "
                "(rollback_id, release_id, version_rollback_sop, database_rollback_migrations, "
                "config_rollback_plan, drill_status, drill_result, plan_hash, "
                "created_at, updated_at) "
                "VALUES (:rollback_id, :release_id, :version_rollback_sop, :database_rollback_migrations, "
                ":config_rollback_plan, :drill_status, :drill_result, :plan_hash, "
                ":created_at, :updated_at)"
            ),
            {
                "rollback_id": str(plan.rollback_id),
                "release_id": str(plan.release_id),
                "version_rollback_sop": plan.version_rollback_sop,
                "database_rollback_migrations": plan.database_rollback_migrations,
                "config_rollback_plan": plan.config_rollback_plan,
                "drill_status": plan.drill_status.value,
                "drill_result": plan.drill_result,
                "plan_hash": plan.plan_hash,
                "created_at": plan.created_at,
                "updated_at": plan.updated_at,
            },
        )

    async def update_drill_status(
        self,
        rollback_id: UUID,
        drill_status: str,
        drill_result: dict | None,
    ) -> None:
        await self._session.execute(
            text(
                "UPDATE rel_rollback_plan "
                "SET drill_status = :drill_status, drill_result = :drill_result, "
                "updated_at = now() WHERE rollback_id = :rollback_id"
            ),
            {
                "rollback_id": str(rollback_id),
                "drill_status": drill_status,
                "drill_result": drill_result,
            },
        )

    async def get_by_release(self, release_id: UUID) -> dict | None:
        result = await self._session.execute(
            text("SELECT * FROM rel_rollback_plan WHERE release_id = :release_id"),
            {"release_id": str(release_id)},
        )
        row = result.first()
        return dict(row._mapping) if row else None