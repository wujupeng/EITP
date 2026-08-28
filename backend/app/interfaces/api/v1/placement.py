"""数据放置与迁移接口 - /api/v1/platform/placement/*。"""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.placement.migration_state import MigrationPhase, MigrationState
from app.domain.placement.placement_manager import PlacementManager
from app.domain.placement.placement_record import PlacementType
from app.infrastructure.db.session import get_db_session
from app.interfaces.schemas.placement import (
    MigrateRequest,
    MigrateResponse,
    MigrationStatusResponse,
    PlacementResponse,
    SetPlacementRequest,
)

router = APIRouter(prefix="/platform/placement", tags=["placement"])

_placement_manager = PlacementManager()
_migration_tasks: dict[UUID, MigrationState] = {}


def _parse_placement(value: str) -> PlacementType:
    try:
        return PlacementType(value)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"未知放置模式: {value}，支持 shared_db/dedicated_db/dedicated_instance",
        )


@router.put("/{tenant_id}", response_model=PlacementResponse)
async def set_placement(
    tenant_id: UUID,
    req: SetPlacementRequest,
    session: AsyncSession = Depends(get_db_session),
) -> PlacementResponse:
    """设置租户数据放置模式（design 2.2.2.7）。

    原子更新 PlacementRecord 并失效连接池缓存。
    """
    placement = _parse_placement(req.placement)
    record = _placement_manager.set_placement(tenant_id, placement)
    return PlacementResponse(
        tenant_id=record.tenant_id,
        placement=record.placement.value,
        connection_target=record.connection_target,
        updated_at=record.updated_at,
    )


@router.get("/{tenant_id}", response_model=PlacementResponse)
async def get_placement(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> PlacementResponse:
    """查询租户数据放置模式。"""
    record = _placement_manager.get_placement(tenant_id)
    if record is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="放置记录不存在")
    return PlacementResponse(
        tenant_id=record.tenant_id,
        placement=record.placement.value,
        connection_target=record.connection_target,
        updated_at=record.updated_at,
    )


@router.post("/{tenant_id}/migrate", response_model=MigrateResponse, status_code=202)
async def migrate(
    tenant_id: UUID,
    req: MigrateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> MigrateResponse:
    """发起在线迁移（异步任务，design 2.2.2.7）。

    四阶段编排：冻结写入 → 全量同步 → 增量同步 → 数据校验 → 原子切换 → 恢复写入。
    """
    _parse_placement(req.target_placement)

    for existing in _migration_tasks.values():
        if existing.tenant_id == tenant_id and existing.is_write_frozen():
            from app.interfaces.middleware.error_handler import DomainError, ErrorCode
            raise DomainError(
                ErrorCode.MIGRATION_IN_PROGRESS,
                "该租户已有迁移任务进行中",
                details={"existing_task_id": str(existing.task_id)},
            )

    task_id = uuid4()
    state = MigrationState(
        task_id=task_id,
        tenant_id=tenant_id,
        target_placement=req.target_placement,
    )
    _migration_tasks[task_id] = state

    return MigrateResponse(
        migration_task_id=task_id,
        tenant_id=tenant_id,
        phase=state.phase.value,
    )


@router.get("/{tenant_id}/migrate/{task_id}/status", response_model=MigrationStatusResponse)
async def get_migration_status(
    tenant_id: UUID,
    task_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> MigrationStatusResponse:
    """查询迁移任务状态。"""
    state = _migration_tasks.get(task_id)
    if state is None or state.tenant_id != tenant_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="迁移任务不存在")
    return MigrationStatusResponse(
        task_id=state.task_id,
        tenant_id=state.tenant_id,
        phase=state.phase.value,
        progress_percent=state.progress_percent,
        started_at=state.started_at,
        completed_at=state.completed_at,
        failure_reason=state.failure_reason,
    )