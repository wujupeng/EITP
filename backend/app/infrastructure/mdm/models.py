"""MDM ORM 模型 - 所有 mdm_* 表。

集团级表无 tenant_id（全平台共享），企业级表含 tenant_id（租户隔离）。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    Text,
    Index,
    UniqueConstraint,
    func,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.dialects.postgresql import JSONB, NUMERIC
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class GroupProductORM(Base):
    __tablename__ = "mdm_group_product"
    __table_args__ = (
        UniqueConstraint("group_product_code", name="uk_mdm_group_product_code"),
        CheckConstraint("status IN ('active', 'disabled')", name="chk_mdm_group_product_status"),
        Index("idx_mdm_group_product_category", "group_category_id"),
        Index("idx_mdm_group_product_brand", "group_brand_id"),
        Index("idx_mdm_group_product_status", "status"),
    )

    group_product_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    group_product_code: Mapped[str] = mapped_column(String(64), nullable=False)
    group_product_name: Mapped[str] = mapped_column(String(256), nullable=False)
    group_category_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    group_brand_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    base_unit_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    spec_template_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    published_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GroupSkuORM(Base):
    __tablename__ = "mdm_group_sku"
    __table_args__ = (
        UniqueConstraint("group_sku_code", name="uk_mdm_group_sku_code"),
        CheckConstraint("status IN ('active', 'disabled')", name="chk_mdm_group_sku_status"),
        Index("idx_mdm_group_sku_product", "group_product_id"),
    )

    group_sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    group_product_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    group_sku_code: Mapped[str] = mapped_column(String(64), nullable=False)
    group_sku_name: Mapped[str] = mapped_column(String(256), nullable=False)
    specification_instance: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    barcode_list: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    unit_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    weight: Mapped[float | None] = mapped_column(NUMERIC(18, 6), nullable=True)
    volume: Mapped[float | None] = mapped_column(NUMERIC(18, 6), nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GroupCategoryORM(Base):
    __tablename__ = "mdm_group_category"
    __table_args__ = (
        UniqueConstraint("group_category_code", name="uk_mdm_group_category_code"),
        CheckConstraint("status IN ('active', 'disabled')", name="chk_mdm_group_category_status"),
        Index("idx_mdm_group_category_parent", "parent_category_id"),
    )

    group_category_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    group_category_code: Mapped[str] = mapped_column(String(64), nullable=False)
    group_category_name: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_category_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    published_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GroupBrandORM(Base):
    __tablename__ = "mdm_group_brand"
    __table_args__ = (
        UniqueConstraint("group_brand_code", name="uk_mdm_group_brand_code"),
    )

    group_brand_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    group_brand_code: Mapped[str] = mapped_column(String(64), nullable=False)
    group_brand_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GroupUnitORM(Base):
    __tablename__ = "mdm_group_unit"
    __table_args__ = (
        UniqueConstraint("group_unit_code", name="uk_mdm_group_unit_code"),
    )

    group_unit_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    group_unit_code: Mapped[str] = mapped_column(String(32), nullable=False)
    group_unit_name: Mapped[str] = mapped_column(String(64), nullable=False)
    is_base_unit: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GroupUnitConversionORM(Base):
    __tablename__ = "mdm_group_unit_conversion"
    __table_args__ = (
        UniqueConstraint("from_unit_id", "to_unit_id", name="uk_mdm_group_unit_conversion"),
    )

    conversion_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    from_unit_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    to_unit_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    ratio: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EnterpriseProductORM(Base):
    __tablename__ = "mdm_enterprise_product"
    __table_args__ = (
        UniqueConstraint("tenant_id", "enterprise_product_code", name="uk_mdm_ep_tenant_code"),
        CheckConstraint("reference_status IN ('active', 'reference_released', 'source_disabled')", name="chk_mdm_ep_ref_status"),
        Index("idx_mdm_ep_tenant", "tenant_id"),
        Index("idx_mdm_ep_group_product", "tenant_id", "group_product_id"),
    )

    enterprise_product_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    group_product_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    enterprise_product_code: Mapped[str] = mapped_column(String(64), nullable=False)
    enterprise_product_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    enterprise_category_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    reference_status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    published_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EnterpriseSkuORM(Base):
    __tablename__ = "mdm_enterprise_sku"
    __table_args__ = (
        UniqueConstraint("tenant_id", "enterprise_sku_code", name="uk_mdm_esku_tenant_code"),
        Index("idx_mdm_esku_tenant", "tenant_id"),
        Index("idx_mdm_esku_product", "tenant_id", "enterprise_product_id"),
    )

    enterprise_sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    enterprise_product_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    group_sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    enterprise_sku_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    enterprise_sku_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    enterprise_barcode_list: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProductReferenceORM(Base):
    __tablename__ = "mdm_product_reference"
    __table_args__ = (
        UniqueConstraint("tenant_id", "group_product_id", name="uk_mdm_ref_tenant_group"),
        CheckConstraint("reference_status IN ('active', 'released', 'source_disabled')", name="chk_mdm_ref_status"),
        Index("idx_mdm_ref_tenant", "tenant_id"),
        Index("idx_mdm_ref_group_product", "group_product_id"),
    )

    reference_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    group_product_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    enterprise_product_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    referenced_by: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    referenced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reference_status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    released_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProductCustomizationORM(Base):
    __tablename__ = "mdm_product_customization"
    __table_args__ = (
        CheckConstraint("inventory_strategy IN ('strict', 'allow', 'warning', 'approval')", name="chk_mdm_cust_inv_strategy"),
        CheckConstraint("cost_model IN ('moving_average', 'weighted_average', 'fifo', 'standard_cost', 'actual_cost')", name="chk_mdm_cust_cost_model"),
        Index("idx_mdm_cust_tenant_product", "tenant_id", "enterprise_product_id"),
        Index("idx_mdm_cust_tenant_sku", "tenant_id", "enterprise_sku_id"),
    )

    customization_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    enterprise_product_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    enterprise_sku_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    sales_price: Mapped[float | None] = mapped_column(NUMERIC(18, 6), nullable=True)
    purchase_price: Mapped[float | None] = mapped_column(NUMERIC(18, 6), nullable=True)
    inventory_strategy: Mapped[str | None] = mapped_column(String(10), nullable=True)
    safety_stock: Mapped[float | None] = mapped_column(NUMERIC(18, 6), nullable=True)
    cost_model: Mapped[str | None] = mapped_column(String(20), nullable=True)
    custom_attributes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EnterpriseCategoryORM(Base):
    __tablename__ = "mdm_enterprise_category"
    __table_args__ = (
        UniqueConstraint("tenant_id", "enterprise_category_code", name="uk_mdm_ec_tenant_code"),
        CheckConstraint("parent_category_level IN ('group', 'enterprise')", name="chk_mdm_ec_parent_level"),
        CheckConstraint("status IN ('active', 'disabled')", name="chk_mdm_ec_status"),
        Index("idx_mdm_ec_tenant", "tenant_id"),
        Index("idx_mdm_ec_parent", "tenant_id", "parent_category_id"),
    )

    enterprise_category_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    enterprise_category_code: Mapped[str] = mapped_column(String(64), nullable=False)
    enterprise_category_name: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_category_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    parent_category_level: Mapped[str | None] = mapped_column(String(10), nullable=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SpecTemplateORM(Base):
    __tablename__ = "mdm_spec_template"
    __table_args__ = (
        CheckConstraint("template_level IN ('group', 'enterprise')", name="chk_mdm_spec_template_level"),
        CheckConstraint("status IN ('active', 'disabled')", name="chk_mdm_spec_template_status"),
        CheckConstraint(
            "(template_level = 'group' AND tenant_id IS NULL) OR (template_level = 'enterprise' AND tenant_id IS NOT NULL)",
            name="chk_mdm_spec_template_tenant",
        ),
        Index("idx_mdm_spec_template_tenant", "tenant_id"),
    )

    template_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    template_level: Mapped[str] = mapped_column(String(10), nullable=False)
    template_code: Mapped[str] = mapped_column(String(64), nullable=False)
    template_name: Mapped[str] = mapped_column(String(128), nullable=False)
    attribute_definitions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AttributeTemplateORM(Base):
    __tablename__ = "mdm_attribute_template"
    __table_args__ = (
        CheckConstraint("template_level IN ('group', 'enterprise')", name="chk_mdm_attr_template_level"),
        CheckConstraint("attribute_type IN ('text', 'number', 'enum', 'date', 'boolean')", name="chk_mdm_attr_template_type"),
        CheckConstraint("status IN ('active', 'disabled')", name="chk_mdm_attr_template_status"),
        CheckConstraint(
            "(template_level = 'group' AND tenant_id IS NULL) OR (template_level = 'enterprise' AND tenant_id IS NOT NULL)",
            name="chk_mdm_attr_template_tenant",
        ),
        Index("idx_mdm_attr_template_tenant", "tenant_id"),
    )

    template_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    template_level: Mapped[str] = mapped_column(String(10), nullable=False)
    template_code: Mapped[str] = mapped_column(String(64), nullable=False)
    template_name: Mapped[str] = mapped_column(String(128), nullable=False)
    attribute_name: Mapped[str] = mapped_column(String(64), nullable=False)
    attribute_type: Mapped[str] = mapped_column(String(10), nullable=False)
    enum_values: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GovernanceWorkflowORM(Base):
    __tablename__ = "mdm_governance_workflow"
    __table_args__ = (
        CheckConstraint("governance_level IN ('group', 'enterprise')", name="chk_mdm_gov_level"),
        CheckConstraint("status IN ('draft', 'submitted', 'approved', 'rejected', 'published', 'rolled_back')", name="chk_mdm_gov_status"),
        CheckConstraint(
            "(governance_level = 'group' AND tenant_id IS NULL) OR (governance_level = 'enterprise' AND tenant_id IS NOT NULL)",
            name="chk_mdm_gov_tenant",
        ),
        Index("idx_mdm_gov_tenant", "tenant_id"),
        Index("idx_mdm_gov_status", "status"),
        Index("idx_mdm_gov_entity", "entity_type", "entity_id"),
    )

    request_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    governance_level: Mapped[str] = mapped_column(String(10), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    target_version_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="draft")
    submitted_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_opinion: Mapped[str | None] = mapped_column(String(512), nullable=True)
    published_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rollback_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    rollback_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rollback_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MasterDataVersionORM(Base):
    __tablename__ = "mdm_master_data_version"
    __table_args__ = (
        CheckConstraint("change_type IN ('create', 'update', 'disable', 'enable', 'publish', 'rollback')", name="chk_mdm_version_change_type"),
        Index("idx_mdm_version_entity", "entity_type", "entity_id", "version_number"),
        Index("idx_mdm_version_tenant", "tenant_id"),
    )

    version_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_before: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    snapshot_after: Mapped[dict] = mapped_column(JSONB, nullable=False)
    change_type: Mapped[str] = mapped_column(String(10), nullable=False)
    operated_by: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    operated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)


class NegativeInventoryPolicyAuditORM(Base):
    __tablename__ = "mdm_negative_inventory_policy_audit"
    __table_args__ = (
        CheckConstraint("policy_before IN ('strict', 'allow', 'warning', 'approval')", name="chk_mdm_nipa_before"),
        CheckConstraint("policy_after IN ('strict', 'allow', 'warning', 'approval')", name="chk_mdm_nipa_after"),
        Index("idx_mdm_nipa_tenant", "tenant_id"),
        Index("idx_mdm_nipa_operated_at", "operated_at"),
    )

    audit_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    policy_before: Mapped[str] = mapped_column(String(10), nullable=False)
    policy_after: Mapped[str] = mapped_column(String(10), nullable=False)
    operated_by: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    operated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reason: Mapped[str] = mapped_column(String(512), nullable=False)


class MasterDataAuditORM(Base):
    __tablename__ = "mdm_master_data_audit"
    __table_args__ = (
        Index("idx_mdm_audit_tenant", "tenant_id"),
        Index("idx_mdm_audit_entity", "entity_type", "entity_id"),
        Index("idx_mdm_audit_operated_at", "operated_at"),
    )

    audit_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    old_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    operated_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    operated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)