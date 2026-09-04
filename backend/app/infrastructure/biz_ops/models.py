"""BIZ-OPS ORM 模型 - SQLAlchemy 2.0 声明式。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base, TenantScopedMixin, TimestampMixin


class BizOpsFeatureSwitchORM(Base, TenantScopedMixin, TimestampMixin):
    """功能开关 ORM - 表 biz_ops_feature_switches。"""

    __tablename__ = "biz_ops_feature_switches"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "feature_key", name="uq_biz_ops_fs_tenant_feature"
        ),
        Index("ix_biz_ops_fs_tenant_scope", "tenant_id", "scope"),
    )

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), nullable=False
    )
    feature_key: Mapped[str] = mapped_column(String(100), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    is_enabled: Mapped[str] = mapped_column(
        String(5), nullable=False, default="true"
    )
    parent_feature_key: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True
    )


class BizOpsBusinessRuleORM(Base, TenantScopedMixin, TimestampMixin):
    """业务规则 ORM - 表 biz_ops_business_rules（当前版本）。"""

    __tablename__ = "biz_ops_business_rules"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "rule_key", name="uq_biz_ops_br_tenant_rule"
        ),
        Index("ix_biz_ops_br_tenant_trigger", "tenant_id", "trigger_point", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), nullable=False
    )
    rule_key: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(200), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_point: Mapped[str] = mapped_column(String(100), nullable=False)
    expression: Mapped[str] = mapped_column(String(2000), nullable=False)
    priority: Mapped[int] = mapped_column(default=100, nullable=False)
    scope_level: Mapped[str] = mapped_column(String(20), nullable=False, default="tenant")
    scope_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[str] = mapped_column(String(5), nullable=False, default="true")
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True
    )


class BizOpsBusinessRuleVersionORM(Base, TenantScopedMixin, TimestampMixin):
    """业务规则版本 ORM - 表 biz_ops_business_rule_versions（历史版本）。"""

    __tablename__ = "biz_ops_business_rule_versions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "rule_key", "version", name="uq_biz_ops_brv_tenant_rule_ver"
        ),
        Index("ix_biz_ops_brv_tenant_rule", "tenant_id", "rule_key"),
    )

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), nullable=False
    )
    rule_key: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(200), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_point: Mapped[str] = mapped_column(String(100), nullable=False)
    expression: Mapped[str] = mapped_column(String(2000), nullable=False)
    priority: Mapped[int] = mapped_column(default=100, nullable=False)
    scope_level: Mapped[str] = mapped_column(String(20), nullable=False, default="tenant")
    scope_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action: Mapped[str | None] = mapped_column(String(20), nullable=True)
    version: Mapped[int] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True
    )


class BizOpsApprovalFlowORM(Base, TenantScopedMixin, TimestampMixin):
    """审批流 ORM - 表 biz_ops_approval_flows。"""
    __tablename__ = "biz_ops_approval_flows"
    __table_args__ = (
        UniqueConstraint("tenant_id", "flow_key", name="uq_biz_ops_af_tenant_flow"),
        Index("ix_biz_ops_af_tenant_entity", "tenant_id", "entity_type"),
    )
    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    flow_key: Mapped[str] = mapped_column(String(100), nullable=False)
    flow_name: Mapped[str] = mapped_column(String(200), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[str] = mapped_column(String(5), nullable=False, default="true")
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


class BizOpsApprovalNodeORM(Base, TenantScopedMixin, TimestampMixin):
    """审批节点 ORM - 表 biz_ops_approval_nodes。"""
    __tablename__ = "biz_ops_approval_nodes"
    __table_args__ = (Index("ix_biz_ops_an_flow_order", "flow_id", "node_order"),)
    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    flow_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    node_order: Mapped[int] = mapped_column(nullable=False)
    node_name: Mapped[str] = mapped_column(String(200), nullable=False)
    routing_strategy: Mapped[str] = mapped_column(String(20), nullable=False)
    routing_config: Mapped[str] = mapped_column(String(2000), nullable=False, default="{}")
    timeout_seconds: Mapped[int] = mapped_column(default=86400, nullable=False)
    timeout_strategy: Mapped[str] = mapped_column(String(20), nullable=False, default="warn_only")
    is_countersign: Mapped[str] = mapped_column(String(5), nullable=False, default="false")
    countersign_ratio: Mapped[float] = mapped_column(default=1.0, nullable=False)
    condition_expression: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class BizOpsApprovalRecordORM(Base, TenantScopedMixin, TimestampMixin):
    """审批记录 ORM - 表 biz_ops_approval_records (append-only)。"""
    __tablename__ = "biz_ops_approval_records"
    __table_args__ = (Index("ix_biz_ops_ar_approval", "approval_id", "node_order"),)
    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    approval_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    flow_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    node_order: Mapped[int] = mapped_column(nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    operator_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class BizOpsPricingStrategyORM(Base, TenantScopedMixin, TimestampMixin):
    """定价策略 ORM - 表 biz_ops_pricing_strategies（当前版本）。"""
    __tablename__ = "biz_ops_pricing_strategies"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "strategy_key", name="uq_biz_ops_ps_tenant_strategy"
        ),
        Index(
            "ix_biz_ops_ps_tenant_type_target_priority",
            "tenant_id", "strategy_type", "target_ref", "priority",
        ),
    )
    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    strategy_key: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(200), nullable=False)
    strategy_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    price_config: Mapped[str] = mapped_column(String(4000), nullable=False, default="{}")
    scope_level: Mapped[str] = mapped_column(String(20), nullable=False, default="tenant")
    scope_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority: Mapped[int] = mapped_column(default=100, nullable=False)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[str] = mapped_column(String(5), nullable=False, default="true")
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)


class BizOpsPricingStrategyVersionORM(Base, TenantScopedMixin, TimestampMixin):
    """定价策略版本 ORM - 表 biz_ops_pricing_strategy_versions（历史版本）。"""
    __tablename__ = "biz_ops_pricing_strategy_versions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "strategy_key", "version",
            name="uq_biz_ops_psv_tenant_strategy_ver",
        ),
        Index("ix_biz_ops_psv_tenant_strategy", "tenant_id", "strategy_key"),
    )
    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    strategy_key: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(200), nullable=False)
    strategy_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    price_config: Mapped[str] = mapped_column(String(4000), nullable=False, default="{}")
    scope_level: Mapped[str] = mapped_column(String(20), nullable=False, default="tenant")
    scope_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority: Mapped[int] = mapped_column(default=100, nullable=False)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)


class BizOpsTaxConfigORM(Base, TenantScopedMixin, TimestampMixin):
    """税务配置 ORM - 表 biz_ops_tax_configs。"""
    __tablename__ = "biz_ops_tax_configs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "config_key", name="uq_biz_ops_tc_tenant_config"),
        Index("ix_biz_ops_tc_tenant_scope", "tenant_id", "scope_level"),
    )
    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    config_key: Mapped[str] = mapped_column(String(100), nullable=False)
    config_name: Mapped[str] = mapped_column(String(200), nullable=False)
    tax_rates: Mapped[str] = mapped_column(String(4000), nullable=False, default="[]")
    tax_flag: Mapped[str] = mapped_column(String(20), nullable=False, default="tax_exclusive")
    direction: Mapped[str] = mapped_column(String(10), nullable=False, default="output")
    scope_level: Mapped[str] = mapped_column(String(20), nullable=False, default="tenant")
    scope_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    special_rules: Mapped[str] = mapped_column(String(2000), nullable=False, default="[]")
    is_active: Mapped[str] = mapped_column(String(5), nullable=False, default="true")
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


class BizOpsInventoryStrategyORM(Base, TenantScopedMixin, TimestampMixin):
    """库存策略 ORM - 表 biz_ops_inventory_strategies（当前版本）。"""
    __tablename__ = "biz_ops_inventory_strategies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "strategy_key", name="uq_biz_ops_is_tenant_strategy"),
        Index("ix_biz_ops_is_tenant_type_target", "tenant_id", "strategy_type", "target_ref"),
    )
    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    strategy_key: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(200), nullable=False)
    strategy_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    threshold_config: Mapped[str] = mapped_column(String(4000), nullable=False, default="{}")
    action_config: Mapped[str] = mapped_column(String(2000), nullable=False, default="{}")
    scope_level: Mapped[str] = mapped_column(String(20), nullable=False, default="tenant")
    scope_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority: Mapped[int] = mapped_column(default=100, nullable=False)
    is_active: Mapped[str] = mapped_column(String(5), nullable=False, default="true")
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


class BizOpsInventoryStrategyVersionORM(Base, TenantScopedMixin, TimestampMixin):
    """库存策略版本 ORM - 表 biz_ops_inventory_strategy_versions（历史版本）。"""
    __tablename__ = "biz_ops_inventory_strategy_versions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "strategy_key", "version",
            name="uq_biz_ops_isv_tenant_strategy_ver",
        ),
        Index("ix_biz_ops_isv_tenant_strategy", "tenant_id", "strategy_key"),
    )
    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    strategy_key: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(200), nullable=False)
    strategy_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    threshold_config: Mapped[str] = mapped_column(String(4000), nullable=False, default="{}")
    action_config: Mapped[str] = mapped_column(String(2000), nullable=False, default="{}")
    scope_level: Mapped[str] = mapped_column(String(20), nullable=False, default="tenant")
    scope_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority: Mapped[int] = mapped_column(default=100, nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


class BizOpsOperationAuditORM(Base, TenantScopedMixin, TimestampMixin):
    """业务操作审计 ORM - 表 biz_ops_operation_audits (append-only, 按月分区)。"""
    __tablename__ = "biz_ops_operation_audits"
    __table_args__ = (
        Index("ix_biz_ops_oa_tenant_op_time", "tenant_id", "operation_type", "occurred_at"),
        Index("ix_biz_ops_oa_tenant_entity", "tenant_id", "entity_type", "entity_id"),
        Index("ix_biz_ops_oa_trace", "trace_id"),
    )
    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    operator_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    audit_data: Mapped[str] = mapped_column(String(8000), nullable=False, default="{}")
