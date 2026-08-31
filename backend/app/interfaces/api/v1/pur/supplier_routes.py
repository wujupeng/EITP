"""供应商管理路由。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.purchasing.pur_app_services import SupplierAppSvc
from app.infrastructure.db.session import get_db_session
from app.infrastructure.purchasing.models import (
    PurSupplierEvaluationORM,
)
from app.infrastructure.purchasing.repositories import (
    SupplierEvaluationRepository,
    SupplierScopeRepository,
)
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.pur import (
    ApproveRequest,
    CreateSupplierRequest,
    PatchSupplierRequest,
    SupplierEvaluationRequest,
    SupplierScopeRequest,
)

router = APIRouter(prefix="/pur/suppliers", tags=["pur-supplier"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


def _get_user_id() -> UUID:
    ctx = SecurityContext.current()
    return ctx.user.user_id if ctx and ctx.user else UUID(int=0)


@router.post("")
@require_permission("pur:supplier:manage")
async def create_supplier(
    req: CreateSupplierRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = SupplierAppSvc(session)
    orm = await svc.create_supplier(
        tenant_id, req.supplier_code, req.supplier_name, req.supplier_type,
        tax_id=req.tax_id, contact_name=req.contact_name, contact_phone=req.contact_phone,
        contact_email=req.contact_email, address_province=req.address_province,
        address_city=req.address_city, address_district=req.address_district,
        address_detail=req.address_detail, bank_name=req.bank_name,
        account_number_masked=req.account_number_masked, bank_branch=req.bank_branch,
    )
    await session.commit()
    return {"supplier_id": str(orm.supplier_id), "supplier_code": orm.supplier_code, "status": orm.status}


@router.get("")
@require_permission("pur:supplier:query")
async def list_suppliers(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = SupplierAppSvc(session)
    items = await svc.list_suppliers(tenant_id, offset, limit)
    return [
        {"supplier_id": str(s.supplier_id), "supplier_code": s.supplier_code,
         "supplier_name": s.supplier_name, "supplier_type": s.supplier_type,
         "status": s.status, "published_version": s.published_version}
        for s in items
    ]


@router.get("/{supplier_id}")
@require_permission("pur:supplier:query")
async def get_supplier(
    supplier_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = SupplierAppSvc(session)
    orm = await svc.get_supplier(tenant_id, supplier_id)
    return {
        "supplier_id": str(orm.supplier_id), "supplier_code": orm.supplier_code,
        "supplier_name": orm.supplier_name, "supplier_type": orm.supplier_type,
        "tax_id": orm.tax_id, "contact_name": orm.contact_name,
        "contact_phone": orm.contact_phone, "contact_email": orm.contact_email,
        "status": orm.status, "published_version": orm.published_version,
        "governance_state": orm.governance_state,
    }


@router.patch("/{supplier_id}")
@require_permission("pur:supplier:manage")
async def patch_supplier(
    supplier_id: UUID,
    req: PatchSupplierRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = SupplierAppSvc(session)
    orm = await svc.get_supplier(tenant_id, supplier_id)
    updates = req.model_dump(exclude_none=True)
    for k, v in updates.items():
        setattr(orm, k, v)
    await session.flush()
    await session.commit()
    return {"supplier_id": str(orm.supplier_id), "status": orm.status}


@router.post("/{supplier_id}/submit")
@require_permission("pur:supplier:manage")
async def submit_supplier(
    supplier_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = SupplierAppSvc(session)
    orm = await svc.get_supplier(tenant_id, supplier_id)
    orm.status = "submitted"
    orm.governance_state = "submitted"
    await session.flush()
    await session.commit()
    return {"supplier_id": str(orm.supplier_id), "status": orm.status}


@router.post("/{supplier_id}/approve")
@require_permission("pur:supplier:manage")
async def approve_supplier(
    supplier_id: UUID,
    req: ApproveRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = SupplierAppSvc(session)
    orm = await svc.get_supplier(tenant_id, supplier_id)
    if not req.approved:
        orm.status = "draft"
        orm.governance_state = "rejected"
    else:
        orm.status = "approved"
        orm.governance_state = "approved"
    await session.flush()
    await session.commit()
    return {"supplier_id": str(orm.supplier_id), "status": orm.status}


@router.post("/{supplier_id}/publish")
@require_permission("pur:supplier:manage")
async def publish_supplier(
    supplier_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = SupplierAppSvc(session)
    orm = await svc.publish_supplier(tenant_id, supplier_id)
    await session.commit()
    return {"supplier_id": str(orm.supplier_id), "status": orm.status, "published_version": orm.published_version}


@router.post("/{supplier_id}/disable")
@require_permission("pur:supplier:manage")
async def disable_supplier(
    supplier_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = SupplierAppSvc(session)
    orm = await svc.disable_supplier(tenant_id, supplier_id)
    await session.commit()
    return {"supplier_id": str(orm.supplier_id), "status": orm.status}


@router.post("/{supplier_id}/scopes")
@require_permission("pur:supplier:manage")
async def add_scope(
    supplier_id: UUID,
    req: SupplierScopeRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = SupplierAppSvc(session)
    orm = await svc.add_scope(
        tenant_id, supplier_id, req.enterprise_sku_id,
        agreement_price=req.agreement_price,
        lead_time_days=req.lead_time_days,
        min_order_qty=req.min_order_qty,
        min_package_qty=req.min_package_qty,
    )
    await session.commit()
    return {"scope_id": str(orm.scope_id), "supplier_id": str(orm.supplier_id), "status": orm.status}


@router.get("/{supplier_id}/scopes")
@require_permission("pur:supplier:query")
async def get_scopes(
    supplier_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    repo = SupplierScopeRepository()
    items = await repo.list_by_supplier(session, tenant_id, supplier_id)
    return [
        {"scope_id": str(s.scope_id), "enterprise_sku_id": str(s.enterprise_sku_id),
         "agreement_price": float(s.agreement_price) if s.agreement_price else None,
         "lead_time_days": s.lead_time_days, "status": s.status}
        for s in items
    ]


@router.post("/{supplier_id}/evaluations")
@require_permission("pur:evaluation:manage")
async def add_evaluation(
    supplier_id: UUID,
    req: SupplierEvaluationRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    overall = (req.on_time_delivery_rate * 40 + req.quality_pass_rate * 40 +
               (req.response_speed_score or 0) / 100 * 20)
    grade = "excellent" if overall >= 90 else "qualified" if overall >= 70 else "unqualified"
    orm = PurSupplierEvaluationORM(
        tenant_id=tenant_id, supplier_id=supplier_id,
        evaluation_period=req.evaluation_period,
        on_time_delivery_rate=req.on_time_delivery_rate,
        quality_pass_rate=req.quality_pass_rate,
        response_speed_score=req.response_speed_score,
        overall_score=overall, grade=grade, evaluated_by=user_id,
    )
    repo = SupplierEvaluationRepository()
    orm = await repo.save(session, orm)
    await session.commit()
    return {"evaluation_id": str(orm.evaluation_id), "grade": orm.grade, "overall_score": float(orm.overall_score)}


@router.get("/{supplier_id}/evaluations")
@require_permission("pur:evaluation:manage")
async def list_evaluations(
    supplier_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    from sqlalchemy import select

    from app.infrastructure.purchasing.models import PurSupplierEvaluationORM
    tenant_id = _get_tenant_id()
    rows = (await session.execute(
        select(PurSupplierEvaluationORM).where(
            PurSupplierEvaluationORM.tenant_id == tenant_id,
            PurSupplierEvaluationORM.supplier_id == supplier_id,
        )
    )).scalars().all()
    return [
        {"evaluation_id": str(e.evaluation_id), "evaluation_period": e.evaluation_period,
         "overall_score": float(e.overall_score), "grade": e.grade}
        for e in rows
    ]