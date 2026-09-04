"""BIZ-OPS 审批流 Schema。"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ApprovalNodeInput(BaseModel):
    node_order: int = Field(..., ge=1, description="节点顺序")
    node_name: str = Field(..., max_length=200, description="节点名称")
    routing_strategy: str = Field(..., max_length=20, description="路由策略")
    routing_config: dict = Field(default_factory=dict, description="路由配置")
    timeout_seconds: int = Field(86400, ge=1, description="超时秒数")
    timeout_strategy: str = Field("warn_only", max_length=20, description="超时策略")
    is_countersign: bool = Field(False, description="是否会签")
    countersign_ratio: float = Field(1.0, ge=0, le=1, description="会签比例")
    condition_expression: str | None = Field(None, max_length=1000, description="条件表达式")


class ApprovalFlowCreateRequest(BaseModel):
    flow_key: str = Field(..., max_length=100, description="审批流键")
    flow_name: str = Field(..., max_length=200, description="审批流名称")
    entity_type: str = Field(..., max_length=50, description="实体类型")
    nodes: list[ApprovalNodeInput] = Field(default_factory=list, description="审批节点")
    description: str | None = Field(None, max_length=500, description="描述")


class ApprovalFlowResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    flow_key: str
    flow_name: str
    entity_type: str
    is_active: bool
    version: int
    description: str | None = None
    node_count: int = 0


class ApprovalActionRequest(BaseModel):
    action: str = Field(..., max_length=20, description="审批操作: approve/reject/return/add_sign/transfer/delegate")
    comment: str | None = Field(None, max_length=1000, description="审批意见")
    delegate_to: UUID | None = Field(None, description="委托/转签目标用户")


class ApprovalActionResponse(BaseModel):
    approval_id: UUID
    status: str
    next_node: int | None = None
    is_final: bool = False