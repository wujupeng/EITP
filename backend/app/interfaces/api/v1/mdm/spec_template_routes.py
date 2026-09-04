"""规格模板路由 - /api/v1/group/spec-templates, /api/v1/tenant/mdm/spec-templates。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.group_catalog.spec_template_app_svc import SpecTemplateAppSvc
from app.domain.group_catalog.aggregates.spec_template_aggregate import (
    AttributeDefinition,
    TemplateLevel,
)
from app.domain.group_catalog.aggregates.attribute_template_aggregate import AttributeType
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.mdm import CreateSpecTemplateRequest, SpecTemplateResponse

router = APIRouter(prefix="/group/spec-templates", tags=["mdm-spec-template"])


@router.post("", response_model=SpecTemplateResponse, status_code=201)
@require_permission("mdm:spec_template:manage")
async def create_spec_template(
    req: CreateSpecTemplateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = SpecTemplateAppSvc(session)
    level = TemplateLevel.GROUP if req.template_level == "group" else TemplateLevel.ENTERPRISE
    defs = [
        AttributeDefinition(
            attribute_name=d.attribute_name,
            attribute_type=AttributeType(d.attribute_type),
            is_required=d.is_required,
            enum_values=d.enum_values,
            min_value=d.min_value,
            max_value=d.max_value,
        )
        for d in req.attribute_definitions
    ]
    agg = await svc.create_template(
        template_code=req.template_code,
        template_name=req.template_name,
        attribute_definitions=defs,
        template_level=level,
        tenant_id=req.tenant_id,
    )
    await session.commit()
    return {
        "template_id": agg.id.value,
        "template_code": agg.template_code,
        "template_name": agg.template_name,
        "template_level": agg.template_level.value,
        "tenant_id": agg.tenant_id,
        "attribute_definitions": [
            {
                "attribute_name": d.attribute_name,
                "attribute_type": d.attribute_type.value,
                "is_required": d.is_required,
                "enum_values": d.enum_values,
                "min_value": d.min_value,
                "max_value": d.max_value,
            }
            for d in agg.attribute_definitions
        ],
        "status": agg.status.value,
    }


@router.get("", response_model=list[dict])
@require_permission("mdm:spec_template:manage")
async def list_spec_templates(
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    svc = SpecTemplateAppSvc(session)
    orms = await svc.list_templates(tenant_id=None)
    return [
        {
            "template_id": str(orm.template_id),
            "template_code": orm.template_code,
            "template_name": orm.template_name,
            "template_level": orm.template_level,
            "tenant_id": str(orm.tenant_id) if orm.tenant_id else None,
            "attribute_definitions": orm.attribute_definitions,
            "status": orm.status,
        }
        for orm in orms
    ]


@router.get("/{template_id}", response_model=dict)
@require_permission("mdm:spec_template:manage")
async def get_spec_template(
    template_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = SpecTemplateAppSvc(session)
    orm = await svc.get_template(template_id)
    if orm is None:
        return {}
    return {
        "template_id": str(orm.template_id),
        "template_code": orm.template_code,
        "template_name": orm.template_name,
        "template_level": orm.template_level,
        "tenant_id": str(orm.tenant_id) if orm.tenant_id else None,
        "attribute_definitions": orm.attribute_definitions,
        "status": orm.status,
    }


enterprise_router = APIRouter(prefix="/tenant/mdm/spec-templates", tags=["mdm-spec-template-enterprise"])


@enterprise_router.get("", response_model=list[dict])
@require_permission("mdm:spec_template:manage")
async def list_enterprise_spec_templates(
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    svc = SpecTemplateAppSvc(session)
    orms = await svc.list_templates(tenant_id=tenant_id)
    return [
        {
            "template_id": str(orm.template_id),
            "template_code": orm.template_code,
            "template_name": orm.template_name,
            "template_level": orm.template_level,
            "tenant_id": str(orm.tenant_id) if orm.tenant_id else None,
            "attribute_definitions": orm.attribute_definitions,
            "status": orm.status,
        }
        for orm in orms
    ]


