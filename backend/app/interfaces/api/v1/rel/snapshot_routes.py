"""资产快照 API 路由 - 3 个接口。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query
from structlog import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/rel/snapshots", tags=["REL-Snapshot"])


@router.get("/{release_id}")
async def list_snapshots(release_id: UUID) -> dict:
    return {"release_id": str(release_id), "snapshots": []}


@router.get("/{release_id}/{snapshot_id}")
async def get_snapshot(release_id: UUID, snapshot_id: UUID) -> dict:
    return {"release_id": str(release_id), "snapshot_id": str(snapshot_id)}


@router.post("/{release_id}/verify-hash")
async def verify_snapshot_hash(release_id: UUID) -> dict:
    logger.info("verify_hash", release_id=str(release_id))
    return {"release_id": str(release_id), "all_verified": True}