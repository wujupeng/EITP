"""BIZ-OPS 业务规则 Schema。"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class BusinessRuleCreateRequest(BaseModel):
    rule_key: str = Field(..., max_length=100, description="规则键")
    rule_name: str = Field(..., max_length=200, description="规则名称")
    rule_type: str = Field(..., max_length=20, description="规则类型: validation/interception/linkage")
    trigger_point: str = Field(..., max_length=100, description="触发点")
    expression: str = Field(..., max_length=2000, description="规则表达式")
    priority: int = Field(100, ge=0, le=999, description="优先级")
    scope_level: str = Field("tenant", max_length=20, description="作用域层级")
    scope_ref: str | None = Field(None, max_length=100, description="作用域引用")
    action: str | None = Field(None, max_length=20, description="拦截动作: reject/warn")
    description: str | None = Field(None, max_length=500, description="描述")


class BusinessRuleUpdateRequest(BaseModel):
    rule_name: str | None = Field(None, max_length=200)
    expression: str | None = Field(None, max_length=2000)
    priority: int | None = Field(None, ge=0, le=999)
    description: str | None = Field(None, max_length=500)


class BusinessRuleResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    rule_key: str
    rule_name: str
    rule_type: str
    trigger_point: str
    expression: str
    priority: int
    scope_level: str
    scope_ref: str | None = None
    action: str | None = None
    is_active: bool
    version: int
    description: str | None = None
