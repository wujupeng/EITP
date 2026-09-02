"""REL Core Freeze 冻结声明仓储。"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.rel.aggregates.core_freeze_declaration_aggregate import (
    CoreFreezeDeclarationAggregate,
)


class CoreFreezeDeclarationRepository:
    """冻结声明仓储。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, declaration: CoreFreezeDeclarationAggregate) -> None:
        await self._session.execute(
            text(
                "INSERT INTO rel_core_freeze_declaration "
                "(declaration_id, release_id, freeze_scope, freeze_time, freeze_baseline_hash, "
                "unfreeze_process_definition, subsequent_milestone_rules, declaration_status, "
                "created_at, updated_at) "
                "VALUES (:declaration_id, :release_id, :freeze_scope, :freeze_time, :freeze_baseline_hash, "
                ":unfreeze_process_definition, :subsequent_milestone_rules, :declaration_status, "
                ":created_at, :updated_at)"
            ),
            {
                "declaration_id": str(declaration.declaration_id),
                "release_id": str(declaration.release_id),
                "freeze_scope": declaration.freeze_scope,
                "freeze_time": declaration.freeze_time,
                "freeze_baseline_hash": declaration.freeze_baseline_hash,
                "unfreeze_process_definition": declaration.unfreeze_process_definition,
                "subsequent_milestone_rules": declaration.subsequent_milestone_rules,
                "declaration_status": declaration.declaration_status.value,
                "created_at": declaration.created_at,
                "updated_at": declaration.updated_at,
            },
        )

    async def update_to_effective(self, declaration_id: UUID) -> None:
        await self._session.execute(
            text(
                "UPDATE rel_core_freeze_declaration "
                "SET declaration_status = 'EFFECTIVE', updated_at = now() "
                "WHERE declaration_id = :declaration_id AND declaration_status = 'DRAFT'"
            ),
            {"declaration_id": str(declaration_id)},
        )

    async def get_by_release(self, release_id: UUID) -> dict | None:
        result = await self._session.execute(
            text("SELECT * FROM rel_core_freeze_declaration WHERE release_id = :release_id"),
            {"release_id": str(release_id)},
        )
        row = result.first()
        return dict(row._mapping) if row else None

    async def list_declarations(
        self,
        declaration_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        conditions: list[str] = []
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if declaration_status is not None:
            conditions.append("declaration_status = :declaration_status")
            params["declaration_status"] = declaration_status
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        result = await self._session.execute(
            text(
                f"SELECT * FROM rel_core_freeze_declaration WHERE {where_clause} "
                f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        return [dict(row._mapping) for row in result.fetchall()]