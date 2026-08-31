"""集团分类与品牌路由 - /api/v1/group/categories, /api/v1/group/brands。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.session import get_db_session
from app.infrastructure.group_catalog.group_product_repository import (
    GroupBrandRepository,
    GroupCategoryRepository,
)
from app.interfaces.middleware.permission_interceptor import require_permission

router = APIRouter(prefix="/group", tags=["mdm-group-category-brand"])


@router.get("/categories", response_model=list[dict])
@require_permission("mdm:group_category:manage")
async def list_group_categories(
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    repo = GroupCategoryRepository()
    orms = await repo.get_tree(session)
    return [
        {
            "group_category_id": str(orm.group_category_id),
            "group_category_code": orm.group_category_code,
            "group_category_name": orm.group_category_name,
            "parent_category_id": str(orm.parent_category_id) if orm.parent_category_id else None,
            "level": orm.level,
            "status": orm.status,
            "published_version": orm.published_version,
        }
        for orm in orms
    ]


@router.get("/brands", response_model=list[dict])
@require_permission("mdm:group_brand:manage")
async def list_group_brands(
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    repo = GroupBrandRepository()
    orms = await repo.list_all(session)
    return [
        {
            "group_brand_id": str(orm.group_brand_id),
            "group_brand_code": orm.group_brand_code,
            "group_brand_name": orm.group_brand_name,
            "status": orm.status,
        }
        for orm in orms
    ]
