"""SAL 结算与发票与收款表 - 结算/对账行/发票/发票行/收款/审计。

Revision ID: 042
Revises: 041
Create Date: 2026-09-01
"""

from __future__ import annotations

from alembic import op

revision = "042"
down_revision = "041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE sal_sales_settlement (
            settlement_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            settlement_code      VARCHAR(64) NOT NULL,
            order_id             UUID NOT NULL REFERENCES sal_sales_order(order_id),
            receivable_amount    NUMERIC(18,6) NOT NULL DEFAULT 0,
            refund_amount        NUMERIC(18,6) NOT NULL DEFAULT 0,
            net_receivable_amount NUMERIC(18,6) NOT NULL DEFAULT 0,
            status               VARCHAR(32) NOT NULL DEFAULT 'pending',
            invoice_id           UUID,
            payment_receipt_id   UUID,
            revenue_landed       BOOLEAN NOT NULL DEFAULT FALSE,
            idempotency_key      VARCHAR(128) NOT NULL DEFAULT '',
            correlation_id       UUID,
            reconciled_by        UUID,
            reconciled_at        TIMESTAMPTZ,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_sal_settlement_code UNIQUE (tenant_id, settlement_code)
        )
    """)
    op.execute("CREATE INDEX idx_sal_settlement_order ON sal_sales_settlement (tenant_id, order_id)")
    op.execute("CREATE INDEX idx_sal_settlement_tenant_status ON sal_sales_settlement (tenant_id, status)")

    op.execute("""
        CREATE TABLE sal_settlement_reconcile_line (
            line_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            settlement_id        UUID NOT NULL REFERENCES sal_sales_settlement(settlement_id),
            line_number          INTEGER NOT NULL DEFAULT 1,
            order_line_id        UUID NOT NULL,
            enterprise_sku_id    UUID NOT NULL,
            ship_quantity        NUMERIC(18,6) NOT NULL DEFAULT 0,
            amount               NUMERIC(18,6) NOT NULL DEFAULT 0,
            diff                 NUMERIC(18,6) NOT NULL DEFAULT 0,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_sal_recline_settlement ON sal_settlement_reconcile_line (tenant_id, settlement_id)")

    op.execute("""
        CREATE TABLE sal_sales_invoice (
            invoice_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            invoice_code         VARCHAR(64) NOT NULL,
            customer_id          UUID NOT NULL REFERENCES sal_customer(customer_id),
            invoice_amount       NUMERIC(18,6) NOT NULL DEFAULT 0,
            tax_amount           NUMERIC(18,6) NOT NULL DEFAULT 0,
            invoice_date         TIMESTAMPTZ NOT NULL DEFAULT now(),
            matched_settlement_id UUID,
            status               VARCHAR(32) NOT NULL DEFAULT 'pending',
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_sal_invoice_code UNIQUE (tenant_id, invoice_code)
        )
    """)
    op.execute("CREATE INDEX idx_sal_invoice_customer ON sal_sales_invoice (tenant_id, customer_id)")
    op.execute("CREATE INDEX idx_sal_invoice_tenant_status ON sal_sales_invoice (tenant_id, status)")

    op.execute("""
        CREATE TABLE sal_invoice_line (
            line_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            invoice_id           UUID NOT NULL REFERENCES sal_sales_invoice(invoice_id),
            line_number          INTEGER NOT NULL DEFAULT 1,
            enterprise_sku_id    UUID NOT NULL,
            quantity             NUMERIC(18,6) NOT NULL,
            unit_price           NUMERIC(18,6) NOT NULL,
            amount               NUMERIC(18,6) NOT NULL DEFAULT 0,
            tax_rate             NUMERIC(6,4) NOT NULL DEFAULT 0,
            tax_amount           NUMERIC(18,6) NOT NULL DEFAULT 0,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_sal_iline_invoice ON sal_invoice_line (tenant_id, invoice_id)")

    op.execute("""
        CREATE TABLE sal_payment_receipt (
            payment_receipt_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            settlement_id        UUID NOT NULL REFERENCES sal_sales_settlement(settlement_id),
            payment_amount       NUMERIC(18,6) NOT NULL DEFAULT 0,
            payment_method       VARCHAR(32) NOT NULL DEFAULT 'bank_transfer',
            payment_date         TIMESTAMPTZ NOT NULL DEFAULT now(),
            bank_account         JSONB NOT NULL DEFAULT '{}'::jsonb,
            status               VARCHAR(32) NOT NULL DEFAULT 'requested',
            payment_no           VARCHAR(128),
            requested_by         UUID,
            requested_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at         TIMESTAMPTZ,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_sal_payment_settlement ON sal_payment_receipt (tenant_id, settlement_id)")
    op.execute("CREATE INDEX idx_sal_payment_tenant_status ON sal_payment_receipt (tenant_id, status)")

    op.execute("""
        CREATE TABLE sal_sales_audit (
            audit_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            user_id              UUID NOT NULL,
            event_type           VARCHAR(64) NOT NULL,
            customer_id          UUID,
            order_id             UUID,
            shipment_id          UUID,
            return_id            UUID,
            settlement_id        UUID,
            invoice_id           UUID,
            payment_id           UUID,
            before_state         JSONB NOT NULL DEFAULT '{}'::jsonb,
            after_state          JSONB NOT NULL DEFAULT '{}'::jsonb,
            wms_picking_id       UUID,
            wms_shipping_id      UUID,
            wms_receiving_id     UUID,
            inv_transaction_ids  JSONB NOT NULL DEFAULT '[]'::jsonb,
            reservation_ids      JSONB NOT NULL DEFAULT '[]'::jsonb,
            reason               VARCHAR(512) NOT NULL DEFAULT '',
            operated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_sal_audit_tenant_time ON sal_sales_audit (tenant_id, operated_at)")
    op.execute("CREATE INDEX idx_sal_audit_tenant_order ON sal_sales_audit (tenant_id, order_id)")
    op.execute("CREATE INDEX idx_sal_audit_tenant_customer ON sal_sales_audit (tenant_id, customer_id)")
    op.execute("CREATE INDEX idx_sal_audit_tenant_event ON sal_sales_audit (tenant_id, event_type)")


def downgrade() -> None:
    for tbl in [
        "sal_sales_audit", "sal_payment_receipt", "sal_invoice_line",
        "sal_sales_invoice", "sal_settlement_reconcile_line", "sal_sales_settlement",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")