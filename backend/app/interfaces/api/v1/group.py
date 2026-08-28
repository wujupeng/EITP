"""集团报表接口 - /api/v1/group/*。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.group.group_report_app_svc import GroupReportAppSvc
from app.domain.group.readonly_boundary import (
    GroupActor,
    OperationType,
    SubsidiaryIsolationGuard,
)
from app.domain.group.summary_snapshot import ReportDimension
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.tenant_context import TenantContext
from app.interfaces.schemas.group import (
    EnforceReadonlyRequest,
    GroupReportResponse,
    PropagateMasterDataRequest,
    PropagateResultResponse,
    UpdateSnapshotRequest,
)

router = APIRouter(prefix="/group", tags=["group"])


def _require_context() -> TenantContext:
    ctx = TenantContext.current()
    if ctx is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="无租户上下文")
    return ctx


@router.get("/reports/{dimension}", response_model=GroupReportResponse)
async def get_group_report(
    dimension: str,
    enterprise_id: UUID = Query(..., description="Enterprise ID"),
    organization_ids: list[UUID] | None = Query(default=None, description="指定子公司列表"),
    session: AsyncSession = Depends(get_db_session),
) -> GroupReportResponse:
    """查询集团汇总报表（spec 5.6 / design 2.2.2.5）。

    优先读 SummarySnapshot，若 snapshot_at 距今 >5 分钟标记 is_delayed=true。
    跨 N 家公司汇总 ≤3s（N≤20，C-PERF-03）。
    """
    _require_context()
    svc = GroupReportAppSvc(session)

    try:
        dim = ReportDimension(dimension)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"未知报表维度: {dimension}")

    org_tuple = tuple(organization_ids) if organization_ids else None
    summary, is_delayed, org_count = await svc.get_group_report(
        enterprise_id=enterprise_id,
        dimension=dim,
        organization_ids=org_tuple,
    )

    return GroupReportResponse(
        enterprise_id=enterprise_id,
        dimension=dimension,
        summary=summary,
        is_delayed=is_delayed,
        organization_count=org_count,
    )


@router.post("/master-data:propagate", response_model=PropagateResultResponse)
async def propagate_master_data(
    req: PropagateMasterDataRequest,
    enterprise_id: UUID = Query(..., description="Enterprise ID"),
    session: AsyncSession = Depends(get_db_session),
) -> PropagateResultResponse:
    """集团主数据下发至子公司（design 2.2.2.5）。

    下发至各子公司并保留公司级属性，编码冲突暂停下发。
    """
    _require_context()
    svc = GroupReportAppSvc(session)

    result = await svc.propagate_master_data(
        enterprise_id=enterprise_id,
        master_data_type=req.master_data_type,
        master_data_id=req.master_data_id,
        target_org_ids=tuple(req.target_org_ids),
    )

    return PropagateResultResponse(
        master_data_type=result.master_data_type,
        master_data_id=result.master_data_id,
        succeeded=list(result.succeeded),
        failed=list(result.failed),
        conflicts=[
            {
                "organization_id": str(c.organization_id),
                "master_data_id": c.master_data_id,
                "reason": c.reason,
            }
            for c in result.conflicts
        ],
        has_conflict=result.has_conflict,
        has_failure=result.has_failure,
    )


@router.post("/snapshots", response_model=GroupReportResponse)
async def update_snapshot(
    req: UpdateSnapshotRequest,
    enterprise_id: UUID = Query(..., description="Enterprise ID"),
    session: AsyncSession = Depends(get_db_session),
) -> GroupReportResponse:
    """更新汇总快照（异步消费者调用，驱动最终一致）。"""
    _require_context()
    svc = GroupReportAppSvc(session)

    try:
        dim = ReportDimension(req.dimension)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"未知报表维度: {req.dimension}")

    snapshot = await svc.update_snapshot(
        enterprise_id=enterprise_id,
        organization_id=req.organization_id,
        dimension=dim,
        snapshot_value=req.snapshot_value,
        source_version=req.source_version,
    )

    return GroupReportResponse(
        enterprise_id=enterprise_id,
        dimension=req.dimension,
        summary=snapshot.snapshot_value,
        is_delayed=False,
        organization_count=1,
    )


@router.post("/readonly-check")
async def enforce_readonly(
    req: EnforceReadonlyRequest,
    enterprise_id: UUID = Query(..., description="Enterprise ID"),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """只读边界校验 - 集团管理员写操作被拒绝。"""
    ctx = _require_context()

    try:
        op = OperationType(req.operation)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"未知操作类型: {req.operation}")

    actor = GroupActor(
        actor_id=ctx.user_id or ctx.tenant_id,
        enterprise_id=enterprise_id,
        is_group_admin=req.is_group_admin,
    )

    svc = GroupReportAppSvc(session)
    await svc.enforce_readonly_boundary(
        actor=actor,
        operation=op,
        target_organization_id=req.target_organization_id,
    )

    return {"enforced": True, "operation": req.operation}