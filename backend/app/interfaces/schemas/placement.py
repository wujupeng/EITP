"""数据放置与迁移请求/响应 Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SetPlacementRequest(BaseModel):
    placement: str = Field(..., examples=["shared_db", "dedicated_db", "dedicated_instance"])


class PlacementResponse(BaseModel):
    tenant_id: UUID
    placement: str
    connection_target: str
    updated_at: datetime


class MigrateRequest(BaseModel):
    target_placement: str = Field(..., examples=["dedicated_db", "dedicated_instance"])
    maintenance_window: str = Field(..., examples="2026-01-01T02:00:00/2026-01-01T04:00:00")


class MigrateResponse(BaseModel):
    migration_task_id: UUID
    tenant_id: UUID
    phase: str
    status: str = "accepted"


class MigrationStatusResponse(BaseModel):
    task_id: UUID
    tenant_id: UUID
    phase: str
    progress_percent: float
    started_at: datetime
    completed_at: datetime | None = None
    failure_reason: str | None = None


class MigrationSuggestionResponse(BaseModel):
    tenant_id: UUID
    suggested_placement: str
    reason: str
    exceeded_metrics: dict[str, Any]