"""属性模板路由 - /api/v1/group/attribute-templates, /api/v1/tenant/mdm/attribute-templates。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.group_catalog.attribute_template_app_svc import (
    AttributeTemplateAppSvc,
)
from app.domain.group_catalog.aggregates.attribute_template_aggregate import (
    AttributeType,
    TemplateLevel,
)
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.mdm import (
    AttributeTemplateResponse,
    CreateAttributeTemplateRequest,
)

router = APIRouter(prefix="/group/attribute-templates", tags=["mdm-attribute-template"])


@router.post("", response_model=AttributeTemplateResponse, status_code=201)
@require_permission("mdm:attribute_template:manage")
async def create_attribute_template(
    req: CreateAttributeTemplateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = AttributeTemplateAppSvc(session)
    level = TemplateLevel.GROUP if req.template_level == "group" else TemplateLevel.ENTERPRISE
    agg = await svc.create_template(
        template_code=req.template_code,
        template_name=req.template_name,
        attribute_name=req.template_code,
        attribute_type=AttributeType(req.attribute_type),
        template_level=level,
        tenant_id=req.tenant_id,
        enum_values=req.enum_values,
        is_required=req.is_required,
    )
    await session.commit()
    return {
        "template_id": agg.id.value,
        "template_code": agg.template_code,
        "template_name": agg.template_name,
        "template_level": agg.template_level.value,
        "tenant_id": agg.tenant_id,
        "attribute_type": agg.attribute_type.value,
        "is_required": agg.is_required,
        "enum_values": agg.enum_values,
        "status": agg.status.value,
    }


@router.get("", response_model=list[dict])
@require_permission("mdm:attribute_template:manage")
async def list_attribute_templates(
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    svc = AttributeTemplateAppSvc(session)
    orms = await svc.list_templates(tenant_id=None)
    return [
        {
            "template_id": str(orm.template_id),
            "template_code": orm.template_code,
            "template_name": orm.template_name,
            "template_level": orm.template_level,
            "tenant_id": str(orm.tenant_id) if orm.tenant_id else None,
            "attribute_type": orm.attribute_type,
            "is_required": orm.is_required,
            "enum_values": orm.enum_values,
            "status": orm.status,
        }
        for orm in orms
    ]


@router.get("/{template_id}", response_model=dict)
@require_permission("mdm:attribute_template:manage")
async def get_attribute_template(
    template_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = AttributeTemplateAppSvc(session)
    orm = await svc.get_template(template_id)
    if orm is None:
        return {}
    return {
        "template_id": str(orm.template_id),
        "template_code": orm.template_code,
        "template_name": orm.template_name,
        "template_level": orm.template_level,
        "tenant_id": str(orm.tenant_id) if orm.tenant_id else None,
        "attribute_type": orm.attribute_type,
        "is_required": orm.is_required,
        "enum_values": orm.enum_values,
        "status": orm.status,
    }


enterprise_router = APIRouter(prefix="/tenant/mdm/attribute-templates", tags=["mdm-attribute-template-enterprise"])


@enterprise_router.get("", response_model=list[dict])
@require_permission("mdm:attribute_template:manage")
async def list_enterprise_attribute_templates(
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    svc = AttributeTemplateAppSvc(session)
    orms = await svc.list_templates(tenant_id=tenant_id)
    return [
        {
            "template_id": str(orm.template_id),
            "template_code": orm.template_code,
            "template_name": orm.template_name,
            "template_level": orm.template_level,
            "tenant_id": str(orm.tenant_id) if orm.tenant_id else None,
            "attribute_type": orm.attribute_type,
            "is_required": orm.is_required,
            "enum_values": orm.enum_values,
            "status": orm.status,
        }
        for orm in orms
    ]


router.include_router(enterprise_router)
