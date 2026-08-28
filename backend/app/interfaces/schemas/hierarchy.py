"""层级管理请求/响应 Schema。"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class CreateNodeRequest(BaseModel):
    level: int = Field(..., ge=1, le=7, description="层级类型 1-7")
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: UUID | None = Field(default=None, description="父节点 ID")


class NodeResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    level: int
    name: str
    parent_id: UUID | None
    is_active: bool


class TreeNodeResponse(NodeResponse):
    children: list[TreeNodeResponse] = Field(default_factory=list)


class DisableNodeResponse(BaseModel):
    node_id: UUID
    disabled_count: int = Field(..., description="被停用的节点总数（含级联）")