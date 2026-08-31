"""集团计量单位路由 - /api/v1/group/units。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.session import get_db_session
from app.infrastructure.group_catalog.group_product_repository import GroupUnitRepository
from app.interfaces.middleware.permission_interceptor import require_permission

router = APIRouter(prefix="/group/units", tags=["mdm-group-unit"])


@router.get("", response_model=list[dict])
@require_permission("mdm:group_unit:manage")
async def list_group_units(
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    repo = GroupUnitRepository()
    orms = await repo.list_all(session)
    return [
        {
            "group_unit_id": str(orm.group_unit_id),
            "group_unit_code": orm.group_unit_code,
            "group_unit_name": orm.group_unit_name,
            "is_base_unit": orm.is_base_unit,
        }
        for orm in orms
    ]
