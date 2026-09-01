"""SAL 销售报价与订单表 - 报价/报价行/订单/订单行（四态守恒）。

Revision ID: 040
Revises: 039
Create Date: 2026-09-01
"""

from __future__ import annotations

from alembic import op

revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE sal_sales_quotation (
            quotation_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            quotation_code       VARCHAR(64) NOT NULL,
            customer_id          UUID NOT NULL REFERENCES sal_customer(customer_id),
            valid_from           TIMESTAMPTZ NOT NULL DEFAULT now(),
            valid_until          TIMESTAMPTZ,
            payment_terms        VARCHAR(256) NOT NULL DEFAULT '',
            currency             VARCHAR(16) NOT NULL DEFAULT 'CNY',
            status               VARCHAR(32) NOT NULL DEFAULT 'draft',
            governance_state     VARCHAR(32) NOT NULL DEFAULT 'draft',
            converted_order_id   UUID,
            submitted_by         UUID,
            submitted_at         TIMESTAMPTZ,
            approved_by          UUID,
            approved_at          TIMESTAMPTZ,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_sal_quotation_code UNIQUE (tenant_id, quotation_code)
        )
    """)
    op.execute("CREATE INDEX idx_sal_quotation_customer ON sal_sales_quotation (tenant_id, customer_id)")
    op.execute("CREATE INDEX idx_sal_quotation_tenant_status ON sal_sales_quotation (tenant_id, status)")

    op.execute("""
        CREATE TABLE sal_sales_quotation_line (
            line_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            quotation_id         UUID NOT NULL REFERENCES sal_sales_quotation(quotation_id),
            line_number          INTEGER NOT NULL DEFAULT 1,
            enterprise_sku_id    UUID NOT NULL,
            quantity             NUMERIC(18,6) NOT NULL,
            unit_price           NUMERIC(18,6) NOT NULL,
            expected_delivery_date TIMESTAMPTZ,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_sal_qline_number UNIQUE (quotation_id, line_number)
        )
    """)
    op.execute("CREATE INDEX idx_sal_qline_quotation ON sal_sales_quotation_line (tenant_id, quotation_id)")

    op.execute("""
        CREATE TABLE sal_sales_order (
            order_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            order_code           VARCHAR(64) NOT NULL,
            customer_id          UUID NOT NULL REFERENCES sal_customer(customer_id),
            source_quotation_id  UUID,
            shipping_warehouse_id UUID,
            payment_terms        VARCHAR(256) NOT NULL DEFAULT '',
            currency             VARCHAR(16) NOT NULL DEFAULT 'CNY',
            total_amount         NUMERIC(18,6) NOT NULL DEFAULT 0,
            status               VARCHAR(32) NOT NULL DEFAULT 'draft',
            reservation_ids      JSONB NOT NULL DEFAULT '[]'::jsonb,
            credit_check_result  JSONB NOT NULL DEFAULT '{}'::jsonb,
            submitted_by         UUID,
            submitted_at         TIMESTAMPTZ,
            approved_by          UUID,
            approved_at          TIMESTAMPTZ,
            version              INTEGER NOT NULL DEFAULT 1,
            idempotency_key      VARCHAR(128) NOT NULL DEFAULT '',
            correlation_id       UUID,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_sal_order_code UNIQUE (tenant_id, order_code)
        )
    """)
    op.execute("CREATE INDEX idx_sal_order_idempotency ON sal_sales_order (tenant_id, idempotency_key)")
    op.execute("CREATE INDEX idx_sal_order_correlation ON sal_sales_order (tenant_id, correlation_id)")
    op.execute("CREATE INDEX idx_sal_order_tenant_status ON sal_sales_order (tenant_id, status)")
    op.execute("CREATE INDEX idx_sal_order_customer_status ON sal_sales_order (tenant_id, customer_id, status)")

    op.execute("""
        CREATE TABLE sal_sales_order_line (
            line_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            order_id             UUID NOT NULL REFERENCES sal_sales_order(order_id),
            line_number          INTEGER NOT NULL DEFAULT 1,
            enterprise_sku_id    UUID NOT NULL,
            ordered_quantity     NUMERIC(18,6) NOT NULL,
            reserved_quantity    NUMERIC(18,6) NOT NULL DEFAULT 0,
            shipped_quantity     NUMERIC(18,6) NOT NULL DEFAULT 0,
            unit_price           NUMERIC(18,6) NOT NULL,
            expected_delivery_date TIMESTAMPTZ,
            pricing_match_result JSONB NOT NULL DEFAULT '{}'::jsonb,
            reservation_id       UUID,
            status               VARCHAR(32) NOT NULL DEFAULT 'open',
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_sal_oline_number UNIQUE (order_id, line_number)
        )
    """)
    op.execute("CREATE INDEX idx_sal_oline_order ON sal_sales_order_line (tenant_id, order_id)")


def downgrade() -> None:
    for tbl in [
        "sal_sales_order_line", "sal_sales_order",
        "sal_sales_quotation_line", "sal_sales_quotation",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")