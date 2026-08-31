"""集团商品路由 - 集团级 /api/v1/group/products。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.group_catalog.group_product_app_svc import GroupProductAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.schemas.mdm import (
    CreateGroupProductRequest,
    CreateGroupSkuRequest,
    GroupProductResponse,
    GroupSkuResponse,
)

router = APIRouter(prefix="/group/products", tags=["mdm-group-product"])


@router.post("", response_model=GroupProductResponse, status_code=201)
@require_permission("mdm:group_product:manage")
async def create_group_product(
    req: CreateGroupProductRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = GroupProductAppSvc(session)
    agg = await svc.create_group_product(
        group_product_code=req.group_product_code,
        group_product_name=req.group_product_name,
        base_unit_id=req.base_unit_id,
        group_category_id=req.group_category_id,
        group_brand_id=req.group_brand_id,
        spec_template_id=req.spec_template_id,
        description=req.description,
    )
    await session.commit()
    return {
        "group_product_id": agg.id.value,
        "group_product_code": agg.group_product_code,
        "group_product_name": agg.group_product_name,
        "base_unit_id": agg.base_unit_id,
        "group_category_id": agg.group_category_id,
        "group_brand_id": agg.group_brand_id,
        "spec_template_id": agg.spec_template_id,
        "status": agg.status.value,
        "published_version": agg.published_version,
        "description": agg.description,
    }


@router.get("", response_model=list[dict])
@require_permission("mdm:group_product:manage")
async def list_group_products(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    svc = GroupProductAppSvc(session)
    orms = await svc.list_group_products(offset=offset, limit=limit)
    return [
        {
            "group_product_id": str(orm.group_product_id),
            "group_product_code": orm.group_product_code,
            "group_product_name": orm.group_product_name,
            "base_unit_id": str(orm.base_unit_id),
            "group_category_id": str(orm.group_category_id) if orm.group_category_id else None,
            "group_brand_id": str(orm.group_brand_id) if orm.group_brand_id else None,
            "spec_template_id": str(orm.spec_template_id) if orm.spec_template_id else None,
            "status": orm.status,
            "published_version": orm.published_version,
            "description": orm.description,
        }
        for orm in orms
    ]


@router.get("/{group_product_id}", response_model=dict)
@require_permission("mdm:group_product:manage")
async def get_group_product(
    group_product_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = GroupProductAppSvc(session)
    orm = await svc.get_group_product(group_product_id)
    if orm is None:
        return {}
    return {
        "group_product_id": str(orm.group_product_id),
        "group_product_code": orm.group_product_code,
        "group_product_name": orm.group_product_name,
        "base_unit_id": str(orm.base_unit_id),
        "group_category_id": str(orm.group_category_id) if orm.group_category_id else None,
        "group_brand_id": str(orm.group_brand_id) if orm.group_brand_id else None,
        "spec_template_id": str(orm.spec_template_id) if orm.spec_template_id else None,
        "status": orm.status,
        "published_version": orm.published_version,
        "description": orm.description,
    }


@router.post("/{group_product_id}/skus", response_model=GroupSkuResponse, status_code=201)
@require_permission("mdm:group_sku:manage")
async def add_group_sku(
    group_product_id: UUID,
    req: CreateGroupSkuRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = GroupProductAppSvc(session)
    sku = await svc.add_group_sku(
        group_product_id=group_product_id,
        group_sku_code=req.group_sku_code,
        group_sku_name=req.group_sku_name,
        unit_id=req.unit_id,
        specification_instance=req.specification_instance,
        barcode_list=req.barcode_list,
        weight=req.weight,
        volume=req.volume,
    )
    await session.commit()
    return {
        "group_sku_id": sku.group_sku_id.value,
        "group_product_id": sku.group_product_id.value,
        "group_sku_code": sku.group_sku_code,
        "group_sku_name": sku.group_sku_name,
        "unit_id": sku.unit_id,
        "specification_instance": sku.specification_instance,
        "barcode_list": sku.barcode_list,
        "weight": sku.weight,
        "volume": sku.volume,
        "status": sku.status.value,
    }


@router.get("/{group_product_id}/skus", response_model=list[dict])
@require_permission("mdm:group_product:manage")
async def list_group_skus(
    group_product_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    svc = GroupProductAppSvc(session)
    orms = await svc.list_group_skus(group_product_id)
    return [
        {
            "group_sku_id": str(orm.group_sku_id),
            "group_product_id": str(orm.group_product_id),
            "group_sku_code": orm.group_sku_code,
            "group_sku_name": orm.group_sku_name,
            "unit_id": str(orm.unit_id),
            "specification_instance": orm.specification_instance,
            "barcode_list": orm.barcode_list,
            "weight": float(orm.weight) if orm.weight else None,
            "volume": float(orm.volume) if orm.volume else None,
            "status": orm.status,
        }
        for orm in orms
    ]


@router.post("/{group_product_id}:disable", response_model=dict)
@require_permission("mdm:group_product:manage")
async def disable_group_product(
    group_product_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = GroupProductAppSvc(session)
    agg = await svc.disable_group_product(group_product_id)
    await session.commit()
    return {
        "group_product_id": agg.id.value,
        "status": agg.status.value,
    }
