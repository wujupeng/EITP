"""MDM Pydantic v2 Schema - 请求/响应模型，强制强类型校验。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ==================== 集团商品目录 ====================

class CreateGroupProductRequest(BaseModel):
    group_product_code: str = Field(..., max_length=64)
    group_product_name: str = Field(..., max_length=256)
    base_unit_id: UUID
    group_category_id: UUID | None = None
    group_brand_id: UUID | None = None
    spec_template_id: UUID | None = None
    description: str | None = Field(None, max_length=1024)


class GroupProductResponse(BaseModel):
    group_product_id: UUID
    group_product_code: str
    group_product_name: str
    base_unit_id: UUID
    group_category_id: UUID | None = None
    group_brand_id: UUID | None = None
    spec_template_id: UUID | None = None
    status: str = "active"
    published_version: int = 1
    description: str | None = None


class CreateGroupSkuRequest(BaseModel):
    group_sku_code: str = Field(..., max_length=64)
    group_sku_name: str = Field(..., max_length=256)
    unit_id: UUID
    specification_instance: dict | None = None
    barcode_list: list[str] | None = None
    weight: float | None = None
    volume: float | None = None


class GroupSkuResponse(BaseModel):
    group_sku_id: UUID
    group_product_id: UUID
    group_sku_code: str
    group_sku_name: str
    unit_id: UUID
    specification_instance: dict | None = None
    barcode_list: list[str] | None = None
    weight: float | None = None
    volume: float | None = None
    status: str = "active"


class CreateGroupCategoryRequest(BaseModel):
    group_category_code: str = Field(..., max_length=64)
    group_category_name: str = Field(..., max_length=128)
    parent_category_id: UUID | None = None
    level: int = Field(1, ge=1)


class GroupCategoryResponse(BaseModel):
    group_category_id: UUID
    group_category_code: str
    group_category_name: str
    parent_category_id: UUID | None = None
    level: int
    status: str = "active"
    published_version: int = 1


class CreateGroupBrandRequest(BaseModel):
    group_brand_code: str = Field(..., max_length=64)
    group_brand_name: str = Field(..., max_length=128)


class GroupBrandResponse(BaseModel):
    group_brand_id: UUID
    group_brand_code: str
    group_brand_name: str
    status: str = "active"


class CreateGroupUnitRequest(BaseModel):
    group_unit_code: str = Field(..., max_length=32)
    group_unit_name: str = Field(..., max_length=64)
    is_base_unit: bool = False


class GroupUnitResponse(BaseModel):
    group_unit_id: UUID
    group_unit_code: str
    group_unit_name: str
    is_base_unit: bool


# ==================== 规格模板与属性模板 ====================

class AttributeDefinitionSchema(BaseModel):
    attribute_name: str = Field(..., max_length=128)
    attribute_type: str = Field(..., pattern="^(text|number|enum|date|boolean)$")
    is_required: bool = False
    enum_values: list[str] | None = None
    min_value: float | None = None
    max_value: float | None = None


class CreateSpecTemplateRequest(BaseModel):
    template_code: str = Field(..., max_length=64)
    template_name: str = Field(..., max_length=256)
    template_level: str = Field("group", pattern="^(group|enterprise)$")
    tenant_id: UUID | None = None
    attribute_definitions: list[AttributeDefinitionSchema]


class SpecTemplateResponse(BaseModel):
    template_id: UUID
    template_code: str
    template_name: str
    template_level: str
    tenant_id: UUID | None = None
    attribute_definitions: list[dict]
    status: str = "active"


class CreateAttributeTemplateRequest(BaseModel):
    template_code: str = Field(..., max_length=64)
    template_name: str = Field(..., max_length=256)
    template_level: str = Field("group", pattern="^(group|enterprise)$")
    tenant_id: UUID | None = None
    attribute_type: str = Field(..., pattern="^(text|number|enum|date|boolean)$")
    is_required: bool = False
    enum_values: list[str] | None = None
    min_value: float | None = None
    max_value: float | None = None


class AttributeTemplateResponse(BaseModel):
    template_id: UUID
    template_code: str
    template_name: str
    template_level: str
    tenant_id: UUID | None = None
    attribute_type: str
    is_required: bool
    enum_values: list[str] | None = None
    status: str = "active"


# ==================== 企业商品引用与定制 ====================

class ReferenceGroupProductRequest(BaseModel):
    group_product_id: UUID
    enterprise_product_code: str = Field(..., max_length=64)
    enterprise_product_name: str | None = Field(None, max_length=256)
    enterprise_category_id: UUID | None = None


class EnterpriseProductResponse(BaseModel):
    enterprise_product_id: UUID
    tenant_id: UUID
    group_product_id: UUID
    enterprise_product_code: str
    enterprise_product_name: str | None = None
    enterprise_category_id: UUID | None = None
    reference_status: str = "active"
    published_version: int = 1


class EnterpriseSkuResponse(BaseModel):
    enterprise_sku_id: UUID
    tenant_id: UUID
    enterprise_product_id: UUID
    group_sku_id: UUID
    enterprise_sku_code: str | None = None
    enterprise_sku_name: str | None = None
    enterprise_barcode_list: list[str] | None = None
    status: str = "active"


class CreateCustomizationRequest(BaseModel):
    enterprise_product_id: UUID
    enterprise_sku_id: UUID | None = None
    sales_price: float | None = Field(None, ge=0)
    purchase_price: float | None = Field(None, ge=0)
    inventory_strategy: str | None = Field(None, pattern="^(strict|allow|warning|approval)$")
    safety_stock: float | None = Field(None, ge=0)
    cost_model: str | None = Field(None, pattern="^(moving_average|weighted_average|fifo|standard_cost|actual_cost)$")
    custom_attributes: dict | None = None


class CustomizationResponse(BaseModel):
    customization_id: UUID
    tenant_id: UUID
    enterprise_product_id: UUID
    enterprise_sku_id: UUID | None = None
    sales_price: float | None = None
    purchase_price: float | None = None
    inventory_strategy: str | None = None
    safety_stock: float | None = None
    cost_model: str | None = None
    custom_attributes: dict | None = None
    version: int = 1


class ProductReferenceResponse(BaseModel):
    reference_id: UUID
    tenant_id: UUID
    group_product_id: UUID
    enterprise_product_id: UUID
    referenced_by: UUID
    referenced_at: datetime
    reference_status: str = "active"
    released_by: UUID | None = None
    released_at: datetime | None = None


# ==================== 治理工作流与版本管理 ====================

class CreateGovernanceRequest(BaseModel):
    entity_type: str = Field(..., max_length=64)
    entity_id: UUID
    governance_level: str = Field("group", pattern="^(group|enterprise)$")
    tenant_id: UUID | None = None
    change_payload: dict
    reason: str = Field(..., min_length=1, max_length=1024)


class GovernanceRequestResponse(BaseModel):
    workflow_id: UUID
    entity_type: str
    entity_id: UUID
    governance_level: str
    tenant_id: UUID | None = None
    state: str = "draft"
    current_version: int = 0
    target_version: int = 1
    submitted_by: UUID | None = None
    approved_by: UUID | None = None
    published_by: UUID | None = None
    reason: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class GovernanceActionRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1024)


class VersionResponse(BaseModel):
    version_id: UUID
    tenant_id: UUID | None = None
    entity_type: str
    entity_id: UUID
    version_number: int
    snapshot_before: dict | None = None
    snapshot_after: dict
    change_type: str
    operated_by: UUID
    reason: str | None = None
    operated_at: datetime


class VersionCompareRequest(BaseModel):
    entity_type: str
    entity_id: UUID
    version_a: int = Field(..., ge=1)
    version_b: int = Field(..., ge=1)


class VersionCompareResponse(BaseModel):
    differences: dict[str, dict]


class VersionRollbackRequest(BaseModel):
    entity_type: str
    entity_id: UUID
    target_version: int = Field(..., ge=1)
    reason: str = Field(..., min_length=1, max_length=1024)


# ==================== 负库存策略 ====================

class NegativePolicyConfigRequest(BaseModel):
    policy_mode: str = Field(..., pattern="^(strict|allow|warning|approval)$")
    reason: str = Field(..., min_length=1, max_length=1024)


class NegativePolicyConfigResponse(BaseModel):
    tenant_id: UUID
    policy_mode: str


class NegativePolicyAuditResponse(BaseModel):
    audit_id: UUID
    tenant_id: UUID
    policy_before: str
    policy_after: str
    operated_by: UUID
    reason: str
    operated_at: datetime


# ==================== 主数据查询与条码定位 ====================

class MasterDataQueryRequest(BaseModel):
    enterprise_product_id: UUID | None = None
    enterprise_product_code: str | None = None
    group_product_id: UUID | None = None
    limit: int = Field(50, ge=1, le=500)


class MasterDataQueryResponse(BaseModel):
    enterprise_product: dict
    group_product: dict | None = None
    enterprise_skus: list[dict] = []
    group_skus: list[dict] = []
    customization: dict | None = None


class BarcodeLocateResponse(BaseModel):
    enterprise_sku_id: UUID
    enterprise_sku_code: str | None = None
    enterprise_product_id: UUID
    barcode_source: str


class MasterDataAuditQueryRequest(BaseModel):
    entity_type: str | None = None
    entity_id: str | None = None
    operated_by: UUID | None = None
    action: str | None = None
    offset: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=500)


class MasterDataAuditResponse(BaseModel):
    audit_id: UUID
    tenant_id: UUID | None = None
    action: str
    entity_type: str
    entity_id: str
    version_number: int | None = None
    old_value: dict | None = None
    new_value: dict | None = None
    operated_by: UUID | None = None
    operated_at: datetime
    reason: str | None = None
    ip_address: str | None = None