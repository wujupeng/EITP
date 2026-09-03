"""冻结声明 API 路由 - 3 个接口。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from structlog import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/rel/declarations", tags=["REL-Declaration"])


@router.post("/{release_id}/issue")
async def issue_declaration(release_id: UUID) -> dict:
    logger.info("issue_declaration", release_id=str(release_id))
    return {
        "release_id": str(release_id),
        "declaration_status": "EFFECTIVE",
        "freeze_type": "PERMANENT",
    }


@router.get("/{release_id}")
async def get_declaration(release_id: UUID) -> dict:
    return {"release_id": str(release_id), "declaration_status": "UNKNOWN"}


@router.get("")
async def list_declarations(
    declaration_status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    return {"declarations": [], "total": 0, "limit": limit, "offset": offset}