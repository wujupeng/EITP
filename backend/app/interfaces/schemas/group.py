"""集团报表请求/响应 Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class GroupReportResponse(BaseModel):
    """集团报表响应 - 含延迟标记。"""

    enterprise_id: UUID
    dimension: str
    summary: dict[str, Any]
    is_delayed: bool = Field(default=False, description="汇总延迟超 5 分钟标记")
    organization_count: int = Field(ge=0)


class PropagateMasterDataRequest(BaseModel):
    """主数据下发请求。"""

    master_data_type: str = Field(..., examples=["sku"])
    master_data_id: str = Field(..., examples=["SKU-001"])
    changes: dict[str, Any] = Field(default_factory=dict)
    target_org_ids: list[UUID] = Field(default_factory=list)


class PropagateResultResponse(BaseModel):
    """主数据下发结果响应。"""

    master_data_type: str
    master_data_id: str
    succeeded: list[UUID]
    failed: list[UUID]
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    has_conflict: bool
    has_failure: bool


class UpdateSnapshotRequest(BaseModel):
    """更新快照请求（内部/异步消费者调用）。"""

    organization_id: UUID
    dimension: str
    snapshot_value: dict[str, Any]
    source_version: int = Field(default=0)


class EnforceReadonlyRequest(BaseModel):
    """只读边界校验请求。"""

    is_group_admin: bool
    operation: str = Field(..., examples=["create", "update", "delete", "read"])
    target_organization_id: UUID