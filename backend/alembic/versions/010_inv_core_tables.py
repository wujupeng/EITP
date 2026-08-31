"""INV inventory and transaction core tables

Revision ID: 010
Revises: 009
Create Date: 2026-08-30 00:00:01
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inv_product",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("product_code", sa.String(50), nullable=False),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("category_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("brand_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("base_unit_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "product_code", name="uq_inv_product_tenant_code"),
    )

    op.create_table(
        "inv_sku",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("product_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("sku_code", sa.String(50), nullable=False),
        sa.Column("sku_name", sa.String(200), nullable=False),
        sa.Column("specification", sa.Text, nullable=True),
        sa.Column("barcode_list", sa.Text, nullable=True),
        sa.Column("unit_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("weight", sa.Float, nullable=True),
        sa.Column("volume", sa.Float, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "sku_code", name="uq_inv_sku_tenant_code"),
    )

    op.create_table(
        "inv_category",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_code", sa.String(50), nullable=False),
        sa.Column("category_name", sa.String(200), nullable=False),
        sa.Column("parent_category_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("level", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "category_code", name="uq_inv_category_tenant_code"),
    )

    op.create_table(
        "inv_brand",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_code", sa.String(50), nullable=False),
        sa.Column("brand_name", sa.String(200), nullable=False),
        sa.Column("logo_url", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "brand_code", name="uq_inv_brand_tenant_code"),
    )

    op.create_table(
        "inv_unit",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("unit_code", sa.String(50), nullable=False),
        sa.Column("unit_name", sa.String(100), nullable=False),
        sa.Column("is_base_unit", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "unit_code", name="uq_inv_unit_tenant_code"),
    )

    op.create_table(
        "inv_location_config",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_type", sa.String(20), nullable=False, server_default="storage"),
        sa.Column("capacity", sa.Float, nullable=True),
        sa.Column("capacity_enforce_mode", sa.String(10), nullable=False, server_default="warn"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "inv_inventory_ledger",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("correlation_id", sa.String(100), nullable=True),
        sa.Column("document_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_type", sa.String(30), nullable=True),
        sa.Column("idempotency_key", sa.String(100), nullable=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("site_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("warehouse_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sku_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_type", sa.String(30), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("quantity_before", sa.Float, nullable=False),
        sa.Column("quantity_change", sa.Float, nullable=False),
        sa.Column("quantity_after", sa.Float, nullable=False),
        sa.Column("unit_cost", sa.Float, nullable=True),
        sa.Column("total_cost", sa.Float, nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("operated_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "quantity_after = quantity_before + quantity_change",
            name="ck_inv_ledger_qty_consistency",
        ),
    )
    op.create_index("ix_inv_ledger_tenant_sku_wh", "inv_inventory_ledger", ["tenant_id", "sku_id", "warehouse_id"])

    op.create_table(
        "inv_inventory_balance",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("batch_no", sa.String(50), nullable=True),
        sa.Column("on_hand", sa.Float, nullable=False, server_default="0"),
        sa.Column("reserved", sa.Float, nullable=False, server_default="0"),
        sa.Column("in_transit", sa.Float, nullable=False, server_default="0"),
        sa.Column("inspection", sa.Float, nullable=False, server_default="0"),
        sa.Column("blocked", sa.Float, nullable=False, server_default="0"),
        sa.Column("unit_cost", sa.Float, nullable=False, server_default="0"),
        sa.Column("last_ledger_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "sku_id", "warehouse_id", "location_id", "batch_no", name="uq_inv_balance_key"),
    )
    op.create_index("ix_inv_balance_tenant_sku_wh", "inv_inventory_balance", ["tenant_id", "sku_id", "warehouse_id"])

    op.create_table(
        "inv_inventory_reservation",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("site_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reserved_quantity", sa.Float, nullable=False),
        sa.Column("remaining_quantity", sa.Float, nullable=False),
        sa.Column("document_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(30), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_inv_reservation_status_expires", "inv_inventory_reservation", ["status", "expires_at"])

    op.create_table(
        "inv_inventory_transaction",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("site_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("transaction_type", sa.String(30), nullable=False),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=True),
        sa.Column("document_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_type", sa.String(30), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("result_ledger_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_inv_tx_tenant_idem", "inv_inventory_transaction", ["tenant_id", "idempotency_key"])

    op.create_table(
        "inv_idempotency_record",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("transaction_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("result", sa.Text, nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_inv_idem_tenant_key"),
    )

    op.create_table(
        "inv_document",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(30), nullable=False),
        sa.Column("document_number", sa.String(50), nullable=False),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("site_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("warehouse_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approved_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("executed_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "document_number", name="uq_inv_doc_tenant_number"),
    )

    op.create_table(
        "inv_document_line",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("sku_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("unit_price", sa.Float, nullable=True),
        sa.Column("warehouse_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("location_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "inv_negative_stock_policy",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mode", sa.String(30), nullable=False, server_default="global_forbid"),
        sa.Column("allow_force", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("require_approval", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("approval_timeout_seconds", sa.Integer, nullable=False, server_default="3600"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", name="uq_inv_neg_policy_tenant"),
    )

    op.create_table(
        "inv_inventory_audit",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("sku_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("warehouse_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("location_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity_before", sa.Float, nullable=True),
        sa.Column("quantity_change", sa.Float, nullable=True),
        sa.Column("quantity_after", sa.Float, nullable=True),
        sa.Column("transaction_type", sa.String(30), nullable=True),
        sa.Column("from_status", sa.String(20), nullable=True),
        sa.Column("to_status", sa.String(20), nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_inv_audit_tenant_sku", "inv_inventory_audit", ["tenant_id", "sku_id"])

    op.execute("REVOKE UPDATE, DELETE ON inv_inventory_ledger FROM PUBLIC")
    op.execute("REVOKE UPDATE, DELETE ON inv_inventory_audit FROM PUBLIC")


def downgrade() -> None:
    op.drop_table("inv_inventory_audit")
    op.drop_table("inv_negative_stock_policy")
    op.drop_table("inv_document_line")
    op.drop_table("inv_document")
    op.drop_table("inv_idempotency_record")
    op.drop_table("inv_inventory_transaction")
    op.drop_table("inv_inventory_reservation")
    op.drop_table("inv_inventory_balance")
    op.drop_table("inv_inventory_ledger")
    op.drop_table("inv_location_config")
    op.drop_table("inv_unit")
    op.drop_table("inv_brand")
    op.drop_table("inv_category")
    op.drop_table("inv_sku")
    op.drop_table("inv_product")