"""SAL 性能索引 - 复合索引 + JSONB GIN 索引支撞性能指标。

Revision ID: 044
Revises: 043
Create Date: 2026-09-01
"""

from __future__ import annotations

from alembic import op

revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 启用 pg_trgm 扩展（模糊查询/相似度匹配） ──
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # ── 客户查询 P95 ≤ 200ms 支撑索引 ──
    op.execute("CREATE INDEX idx_sal_customer_name_trgm ON sal_customer USING gin (customer_name gin_trgm_ops)")
    op.execute("CREATE INDEX idx_sal_customer_type_status ON sal_customer (tenant_id, customer_type, status)")

    # ── 价格体系匹配优先级索引 ──
    op.execute("CREATE INDEX idx_sal_pricing_sku_status_priority ON sal_customer_pricing (tenant_id, enterprise_sku_id, status, priority)")

    # ── 信用额度查询索引 ──
    op.execute("CREATE INDEX idx_sal_credit_limit_tenant ON sal_credit_limit (tenant_id)")

    # ── 销售报价查询索引 ──
    op.execute("CREATE INDEX idx_sal_quotation_valid ON sal_sales_quotation (tenant_id, status, valid_from, valid_until)")
    op.execute("CREATE INDEX idx_sal_quotation_converted ON sal_sales_quotation (tenant_id, converted_order_id)")

    # ── 销售订单查询 P95 ≤ 300ms 支撑索引 ──
    op.execute("CREATE INDEX idx_sal_order_customer_created ON sal_sales_order (tenant_id, customer_id, created_at DESC)")
    op.execute("CREATE INDEX idx_sal_order_status_created ON sal_sales_order (tenant_id, status, created_at DESC)")
    op.execute("CREATE INDEX idx_sal_order_source_quotation ON sal_sales_order (tenant_id, source_quotation_id)")

    # ── 销售订单详情查询 P95 ≤ 500ms 支撑索引 ──
    op.execute("CREATE INDEX idx_sal_oline_order_sku ON sal_sales_order_line (tenant_id, order_id, enterprise_sku_id)")
    op.execute("CREATE INDEX idx_sal_oline_status ON sal_sales_order_line (tenant_id, status)")

    # ── 发货单查询索引 ──
    op.execute("CREATE INDEX idx_sal_shipment_order_ids_gin ON sal_shipment_order USING gin (order_ids)")
    op.execute("CREATE INDEX idx_sal_shipment_warehouse_status ON sal_shipment_order (tenant_id, shipping_warehouse_id, status)")
    op.execute("CREATE INDEX idx_sal_shipment_created ON sal_shipment_order (tenant_id, created_at DESC)")

    # ── 退货查询索引 ──
    op.execute("CREATE INDEX idx_sal_return_shipment ON sal_sales_return (tenant_id, original_shipment_id)")
    op.execute("CREATE INDEX idx_sal_return_created ON sal_sales_return (tenant_id, created_at DESC)")

    # ── 结算查询索引 ──
    op.execute("CREATE INDEX idx_sal_settlement_invoice ON sal_sales_settlement (tenant_id, invoice_id)")
    op.execute("CREATE INDEX idx_sal_settlement_payment ON sal_sales_settlement (tenant_id, payment_receipt_id)")
    op.execute("CREATE INDEX idx_sal_settlement_revenue ON sal_sales_settlement (tenant_id, revenue_landed)")

    # ── 发票查询索引 ──
    op.execute("CREATE INDEX idx_sal_invoice_settlement ON sal_sales_invoice (tenant_id, matched_settlement_id)")
    op.execute("CREATE INDEX idx_sal_invoice_date ON sal_sales_invoice (tenant_id, invoice_date DESC)")

    # ── 收款查询索引 ──
    op.execute("CREATE INDEX idx_sal_payment_no ON sal_payment_receipt (tenant_id, payment_no)")
    op.execute("CREATE INDEX idx_sal_payment_completed ON sal_payment_receipt (tenant_id, completed_at)")

    # ── 审计多维度检索索引 ──
    op.execute("CREATE INDEX idx_sal_audit_shipment ON sal_sales_audit (tenant_id, shipment_id)")
    op.execute("CREATE INDEX idx_sal_audit_return ON sal_sales_audit (tenant_id, return_id)")
    op.execute("CREATE INDEX idx_sal_audit_settlement ON sal_sales_audit (tenant_id, settlement_id)")
    op.execute("CREATE INDEX idx_sal_audit_invoice ON sal_sales_audit (tenant_id, invoice_id)")
    op.execute("CREATE INDEX idx_sal_audit_payment ON sal_sales_audit (tenant_id, payment_id)")


def downgrade() -> None:
    for idx in [
        "idx_sal_audit_payment", "idx_sal_audit_invoice", "idx_sal_audit_settlement",
        "idx_sal_audit_return", "idx_sal_audit_shipment",
        "idx_sal_payment_completed", "idx_sal_payment_no",
        "idx_sal_invoice_date", "idx_sal_invoice_settlement",
        "idx_sal_settlement_revenue", "idx_sal_settlement_payment", "idx_sal_settlement_invoice",
        "idx_sal_return_created", "idx_sal_return_shipment",
        "idx_sal_shipment_created", "idx_sal_shipment_warehouse_status", "idx_sal_shipment_order_ids_gin",
        "idx_sal_oline_status", "idx_sal_oline_order_sku",
        "idx_sal_order_source_quotation", "idx_sal_order_status_created", "idx_sal_order_customer_created",
        "idx_sal_quotation_converted", "idx_sal_quotation_valid",
        "idx_sal_credit_limit_tenant",
        "idx_sal_pricing_sku_status_priority",
        "idx_sal_customer_type_status", "idx_sal_customer_name_trgm",
    ]:
        op.execute(f"DROP INDEX IF EXISTS {idx}")