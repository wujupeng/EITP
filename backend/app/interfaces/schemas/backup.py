"""备份与恢复请求/响应 Schema。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BackupResponse(BaseModel):
    backup_id: UUID
    tenant_id: UUID
    backup_type: str
    storage_uri: str
    checksum: str
    status: str
    created_at: datetime
    expires_at: datetime
    size_bytes: int = 0
    failure_reason: str | None = None


class BackupTriggerResponse(BaseModel):
    backup_id: UUID
    status: str = "accepted"


class RestoreRequest(BaseModel):
    target_tenant_id: UUID
    expected_checksum: str = ""


class RestoreResponse(BaseModel):
    restore_task_id: UUID
    backup_id: UUID
    status: str = "accepted"


class SetRetentionPolicyRequest(BaseModel):
    retain_days: int = Field(default=30, ge=1, le=3650)
    retain_copies: int = Field(default=10, ge=1, le=100)


class RetentionPolicyResponse(BaseModel):
    tenant_id: UUID
    retain_days: int
    retain_copies: int