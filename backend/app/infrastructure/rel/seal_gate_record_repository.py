"""REL 封版门禁记录仓储 - 仅 INSERT，无 update/delete。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.rel.aggregates.seal_gate_record_aggregate import SealGateRecordAggregate


class SealGateRecordRepository:
    """门禁记录仓储 - append-only。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, record: SealGateRecordAggregate) -> None:
        await self._session.execute(
            text(
                "INSERT INTO rel_seal_gate_record "
                "(gate_id, release_id, gate_type, gate_result, gate_detail, "
                "gate_time, executed_by, created_at) "
                "VALUES (:gate_id, :release_id, :gate_type, :gate_result, :gate_detail, "
                ":gate_time, :executed_by, :created_at)"
            ),
            {
                "gate_id": str(record.gate_id),
                "release_id": str(record.release_id),
                "gate_type": record.gate_type.value,
                "gate_result": record.gate_result,
                "gate_detail": record.gate_detail,
                "gate_time": record.gate_time,
                "executed_by": record.executed_by,
                "created_at": record.created_at,
            },
        )

    async def get_by_release(self, release_id: UUID) -> list[dict]:
        result = await self._session.execute(
            text(
                "SELECT * FROM rel_seal_gate_record "
                "WHERE release_id = :release_id ORDER BY gate_time ASC"
            ),
            {"release_id": str(release_id)},
        )
        return [dict(row._mapping) for row in result.fetchall()]