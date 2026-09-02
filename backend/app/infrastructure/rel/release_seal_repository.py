"""REL 封版记录仓储 - 仅 INSERT，无 update/delete。"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.rel.aggregates.release_seal_aggregate import ReleaseSealAggregate


class ReleaseSealRepository:
    """封版记录仓储 - append-only。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, seal: ReleaseSealAggregate) -> None:
        await self._session.execute(
            text(
                "INSERT INTO rel_release "
                "(release_id, release_number, version, git_tag, git_commit_sha, "
                "seal_time, seal_status, verdict, signed_by_releaser, signed_by_security, "
                "signed_at, core_freeze_baseline_hash, test_total_count, test_passed_count, "
                "evidence_hash, created_at, updated_at) "
                "VALUES (:release_id, :release_number, :version, :git_tag, :git_commit_sha, "
                ":seal_time, :seal_status, :verdict, :signed_by_releaser, :signed_by_security, "
                ":signed_at, :core_freeze_baseline_hash, :test_total_count, :test_passed_count, "
                ":evidence_hash, :created_at, :updated_at)"
            ),
            {
                "release_id": str(seal.release_id),
                "release_number": seal.release_number,
                "version": seal.version,
                "git_tag": seal.git_tag,
                "git_commit_sha": seal.git_commit_sha,
                "seal_time": seal.seal_time,
                "seal_status": seal.seal_status.value,
                "verdict": seal.verdict.value if seal.verdict else None,
                "signed_by_releaser": seal.signed_by_releaser,
                "signed_by_security": seal.signed_by_security,
                "signed_at": seal.signed_at,
                "core_freeze_baseline_hash": seal.core_freeze_baseline_hash,
                "test_total_count": seal.test_total_count,
                "test_passed_count": seal.test_passed_count,
                "evidence_hash": seal.evidence_hash,
                "created_at": seal.created_at,
                "updated_at": seal.updated_at,
            },
        )

    async def get_by_id(self, release_id: UUID) -> dict | None:
        result = await self._session.execute(
            text("SELECT * FROM rel_release WHERE release_id = :release_id"),
            {"release_id": str(release_id)},
        )
        row = result.first()
        return dict(row._mapping) if row else None

    async def list_seals(
        self,
        seal_status: str | None = None,
        verdict: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        conditions: list[str] = []
        params: dict[str, Any] = {}
        if seal_status is not None:
            conditions.append("seal_status = :seal_status")
            params["seal_status"] = seal_status
        if verdict is not None:
            conditions.append("verdict = :verdict")
            params["verdict"] = verdict
        if start_time is not None:
            conditions.append("created_at >= :start_time")
            params["start_time"] = start_time
        if end_time is not None:
            conditions.append("created_at <= :end_time")
            params["end_time"] = end_time
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params["limit"] = limit
        params["offset"] = offset
        result = await self._session.execute(
            text(
                f"SELECT * FROM rel_release WHERE {where_clause} "
                f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        return [dict(row._mapping) for row in result.fetchall()]