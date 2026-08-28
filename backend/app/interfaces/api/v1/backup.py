"""备份与恢复接口 - /api/v1/platform/backup/*。"""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.backup.backup_record import BackupRecord, BackupType, RetentionPolicy
from app.infrastructure.db.session import get_db_session
from app.interfaces.schemas.backup import (
    BackupResponse,
    BackupTriggerResponse,
    RestoreRequest,
    RestoreResponse,
    RetentionPolicyResponse,
    SetRetentionPolicyRequest,
)

router = APIRouter(prefix="/platform/backup", tags=["backup"])

_backup_records: dict[UUID, BackupRecord] = {}
_retention_policies: dict[UUID, RetentionPolicy] = {}


@router.post("/{tenant_id}", response_model=BackupTriggerResponse, status_code=202)
async def trigger_backup(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> BackupTriggerResponse:
    """触发租户级独立备份（design 2.2.2.8）。"""
    policy = _retention_policies.get(tenant_id)
    retain_days = policy.retain_days if policy else 30

    record = BackupRecord.create(
        tenant_id=tenant_id,
        backup_type=BackupType.FULL,
        retain_days=retain_days,
    )
    _backup_records[record.backup_id] = record

    return BackupTriggerResponse(backup_id=record.backup_id)


@router.get("/{tenant_id}/list", response_model=list[BackupResponse])
async def list_backups(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[BackupResponse]:
    """查询租户备份列表。"""
    records = [r for r in _backup_records.values() if r.tenant_id == tenant_id]
    return [_to_response(r) for r in records]


@router.post("/{backup_id}/restore", response_model=RestoreResponse, status_code=202)
async def restore_backup(
    backup_id: UUID,
    req: RestoreRequest,
    session: AsyncSession = Depends(get_db_session),
) -> RestoreResponse:
    """恢复租户至备份时点（design 2.2.2.8）。

    禁止跨租户恢复（C-BACKUP-01）。
    """
    from app.domain.backup.restore_guard import RestoreGuard

    backup = _backup_records.get(backup_id)
    if backup is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="备份记录不存在")

    RestoreGuard.enforce_same_tenant(backup, req.target_tenant_id)
    RestoreGuard.enforce_completed(backup)
    if req.expected_checksum:
        RestoreGuard.enforce_integrity(backup, req.expected_checksum)

    return RestoreResponse(
        restore_task_id=uuid4(),
        backup_id=backup_id,
    )


@router.put("/{tenant_id}/retention", response_model=RetentionPolicyResponse)
async def set_retention_policy(
    tenant_id: UUID,
    req: SetRetentionPolicyRequest,
    session: AsyncSession = Depends(get_db_session),
) -> RetentionPolicyResponse:
    """配置备份保留策略（design 2.2.2.8）。"""
    policy = RetentionPolicy(
        tenant_id=tenant_id,
        retain_days=req.retain_days,
        retain_copies=req.retain_copies,
    )
    _retention_policies[tenant_id] = policy

    return RetentionPolicyResponse(
        tenant_id=tenant_id,
        retain_days=policy.retain_days,
        retain_copies=policy.retain_copies,
    )


def _to_response(record: BackupRecord) -> BackupResponse:
    return BackupResponse(
        backup_id=record.backup_id,
        tenant_id=record.tenant_id,
        backup_type=record.backup_type.value,
        storage_uri=record.storage_uri,
        checksum=record.checksum,
        status=record.status.value,
        created_at=record.created_at,
        expires_at=record.expires_at,
        size_bytes=record.size_bytes,
        failure_reason=record.failure_reason,
    )