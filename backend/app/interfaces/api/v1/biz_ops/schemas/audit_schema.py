"""BIZ-OPS 审计查询 Schema。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OperationAuditRecord(BaseModel):
    """操作审计记录。"""
    id: UUID
    tenant_id: UUID
    trace_id: str
    operation_type: str
    operator_id: UUID
    entity_type: str
    entity_id: UUID
    occurred_at: datetime
    audit_data: dict


class PaginatedResponse(BaseModel):
    """分页响应。"""
    items: list[dict] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class AuditQueryParams(BaseModel):
    """审计查询参数。"""
    operation_type: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)