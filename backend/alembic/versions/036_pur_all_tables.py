"""PUR 采购管理表 - 供应商/报价/评估/申请/订单/到货/退货/结算/发票/付款/审计/对账。

Revision ID: 036
Revises: 035
Create Date: 2026-08-31
"""

from __future__ import annotations

from alembic import op

revision = "036"
down_revision = "035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE pur_supplier (
            supplier_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            supplier_code        VARCHAR(64) NOT NULL,
            supplier_name        VARCHAR(256) NOT NULL,
            supplier_type        VARCHAR(32) NOT NULL DEFAULT 'distributor',
            tax_id               VARCHAR(64) NOT NULL DEFAULT '',
            contact_name         VARCHAR(128) NOT NULL DEFAULT '',
            contact_phone        VARCHAR(32) NOT NULL DEFAULT '',
            contact_email        VARCHAR(128) NOT NULL DEFAULT '',
            address_province     VARCHAR(64) NOT NULL DEFAULT '',
            address_city         VARCHAR(64) NOT NULL DEFAULT '',
            address_district     VARCHAR(64) NOT NULL DEFAULT '',
            address_detail       VARCHAR(256) NOT NULL DEFAULT '',
            bank_name            VARCHAR(128) NOT NULL DEFAULT '',
            account_number_masked VARCHAR(64) NOT NULL DEFAULT '',
            bank_branch          VARCHAR(128) NOT NULL DEFAULT '',
            status               VARCHAR(16) NOT NULL DEFAULT 'draft',
            published_version    INTEGER NOT NULL DEFAULT 0,
            governance_state     VARCHAR(32) NOT NULL DEFAULT 'draft',
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_pur_supplier_code UNIQUE (tenant_id, supplier_code)
        )
    """)
    op.execute("CREATE INDEX idx_pur_supplier_tenant_status ON pur_supplier (tenant_id, status)")

    op.execute("""
        CREATE TABLE pur_supplier_scope (
            scope_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            supplier_id          UUID NOT NULL REFERENCES pur_supplier(supplier_id),
            enterprise_sku_id    UUID NOT NULL,
            agreement_price      NUMERIC(18,6),
            lead_time_days       INTEGER,
            min_order_qty        NUMERIC(18,6),
            min_package_qty      NUMERIC(18,6),
            status               VARCHAR(16) NOT NULL DEFAULT 'active',
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_pur_scope_sku UNIQUE (tenant_id, supplier_id, enterprise_sku_id)
        )
    """)
    op.execute("CREATE INDEX idx_pur_scope_supplier ON pur_supplier_scope (tenant_id, supplier_id)")

    op.execute("""
        CREATE TABLE pur_quotation (
            quotation_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            supplier_id          UUID NOT NULL REFERENCES pur_supplier(supplier_id),
            quotation_code       VARCHAR(64) NOT NULL,
            valid_from           TIMESTAMPTZ NOT NULL DEFAULT now(),
            valid_until          TIMESTAMPTZ,
            payment_terms        VARCHAR(256) NOT NULL DEFAULT '',
            status               VARCHAR(16) NOT NULL DEFAULT 'draft',
            governance_state     VARCHAR(32) NOT NULL DEFAULT 'draft',
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_pur_quotation_code UNIQUE (tenant_id, quotation_code)
        )
    """)
    op.execute("CREATE INDEX idx_pur_quotation_supplier ON pur_quotation (tenant_id, supplier_id)")

    op.execute("""
        CREATE TABLE pur_quotation_line (
            line_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            quotation_id         UUID NOT NULL REFERENCES pur_quotation(quotation_id),
            sku_id               UUID NOT NULL,
            unit_price           NUMERIC(18,6) NOT NULL,
            lead_time_days       INTEGER NOT NULL DEFAULT 0,
            min_order_qty        NUMERIC(18,6) NOT NULL DEFAULT 1,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_pur_qline_quotation ON pur_quotation_line (tenant_id, quotation_id)")

    op.execute("""
        CREATE TABLE pur_supplier_evaluation (
            evaluation_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            supplier_id          UUID NOT NULL REFERENCES pur_supplier(supplier_id),
            evaluation_period    VARCHAR(16) NOT NULL,
            on_time_delivery_rate NUMERIC(6,4) NOT NULL DEFAULT 0,
            quality_pass_rate    NUMERIC(6,4) NOT NULL DEFAULT 0,
            response_speed_score NUMERIC(6,2),
            overall_score        NUMERIC(6,2) NOT NULL DEFAULT 0,
            grade                VARCHAR(16) NOT NULL DEFAULT 'unqualified',
            evaluated_by         UUID,
            evaluated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_pur_eval_supplier_period ON pur_supplier_evaluation (tenant_id, supplier_id, evaluation_period)")

    op.execute("""
        CREATE TABLE pur_purchase_request (
            request_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            request_code         VARCHAR(64) NOT NULL,
            title                VARCHAR(256) NOT NULL DEFAULT '',
            department_id        UUID,
            budget_id            UUID,
            total_amount         NUMERIC(18,6) NOT NULL DEFAULT 0,
            status               VARCHAR(16) NOT NULL DEFAULT 'draft',
            approved_by          UUID,
            approved_at          TIMESTAMPTZ,
            converted_order_id   UUID,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_pur_request_code UNIQUE (tenant_id, request_code)
        )
    """)
    op.execute("CREATE INDEX idx_pur_request_tenant_status ON pur_purchase_request (tenant_id, status)")

    op.execute("""
        CREATE TABLE pur_purchase_request_line (
            line_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            request_id           UUID NOT NULL REFERENCES pur_purchase_request(request_id),
            sku_id               UUID NOT NULL,
            quantity             NUMERIC(18,6) NOT NULL,
            unit_price           NUMERIC(18,6),
            remark               VARCHAR(512) NOT NULL DEFAULT '',
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_pur_reqline_request ON pur_purchase_request_line (tenant_id, request_id)")

    op.execute("""
        CREATE TABLE pur_purchase_order (
            order_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            order_code           VARCHAR(64) NOT NULL,
            supplier_id          UUID NOT NULL REFERENCES pur_supplier(supplier_id),
            warehouse_id         UUID,
            request_id           UUID,
            total_amount         NUMERIC(18,6) NOT NULL DEFAULT 0,
            status               VARCHAR(16) NOT NULL DEFAULT 'draft',
            approved_by          UUID,
            sent_at              TIMESTAMPTZ,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_pur_order_code UNIQUE (tenant_id, order_code)
        )
    """)
    op.execute("CREATE INDEX idx_pur_order_tenant_status ON pur_purchase_order (tenant_id, status)")
    op.execute("CREATE INDEX idx_pur_order_supplier ON pur_purchase_order (tenant_id, supplier_id)")

    op.execute("""
        CREATE TABLE pur_purchase_order_line (
            line_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            order_id             UUID NOT NULL REFERENCES pur_purchase_order(order_id),
            sku_id               UUID NOT NULL,
            ordered_quantity     NUMERIC(18,6) NOT NULL,
            received_quantity    NUMERIC(18,6) NOT NULL DEFAULT 0,
            unit_price           NUMERIC(18,6) NOT NULL,
            lead_time_days       INTEGER NOT NULL DEFAULT 0,
            remark               VARCHAR(512) NOT NULL DEFAULT '',
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_pur_orderline_order ON pur_purchase_order_line (tenant_id, order_id)")

    op.execute("""
        CREATE TABLE pur_asn (
            asn_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            asn_code             VARCHAR(64) NOT NULL,
            order_id             UUID NOT NULL REFERENCES pur_purchase_order(order_id),
            supplier_id          UUID NOT NULL,
            warehouse_id         UUID NOT NULL,
            status               VARCHAR(16) NOT NULL DEFAULT 'draft',
            sent_at              TIMESTAMPTZ,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_pur_asn_code UNIQUE (tenant_id, asn_code)
        )
    """)
    op.execute("CREATE INDEX idx_pur_asn_order ON pur_asn (tenant_id, order_id)")

    op.execute("""
        CREATE TABLE pur_asn_line (
            line_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            asn_id               UUID NOT NULL REFERENCES pur_asn(asn_id),
            order_line_id        UUID NOT NULL,
            sku_id               UUID NOT NULL,
            expected_quantity    NUMERIC(18,6) NOT NULL,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_pur_asnline_asn ON pur_asn_line (tenant_id, asn_id)")

    op.execute("""
        CREATE TABLE pur_purchase_receipt (
            receipt_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            receipt_code         VARCHAR(64) NOT NULL,
            order_id             UUID NOT NULL REFERENCES pur_purchase_order(order_id),
            asn_id               UUID,
            supplier_id          UUID NOT NULL,
            warehouse_id         UUID NOT NULL,
            status               VARCHAR(16) NOT NULL DEFAULT 'pending',
            wms_receiving_id     UUID,
            inv_transaction_ids  JSONB NOT NULL DEFAULT '[]'::jsonb,
            confirmed_at         TIMESTAMPTZ,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_pur_receipt_code UNIQUE (tenant_id, receipt_code)
        )
    """)
    op.execute("CREATE INDEX idx_pur_receipt_order ON pur_purchase_receipt (tenant_id, order_id)")

    op.execute("""
        CREATE TABLE pur_purchase_receipt_line (
            line_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            receipt_id           UUID NOT NULL REFERENCES pur_purchase_receipt(receipt_id),
            order_line_id        UUID NOT NULL,
            sku_id               UUID NOT NULL,
            received_quantity    NUMERIC(18,6) NOT NULL,
            qc_result            VARCHAR(16) NOT NULL DEFAULT '',
            wms_receiving_id     UUID,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_pur_recline_receipt ON pur_purchase_receipt_line (tenant_id, receipt_id)")

    op.execute("""
        CREATE TABLE pur_purchase_return (
            return_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            return_code          VARCHAR(64) NOT NULL,
            order_id             UUID NOT NULL REFERENCES pur_purchase_order(order_id),
            supplier_id          UUID NOT NULL,
            warehouse_id         UUID,
            status               VARCHAR(16) NOT NULL DEFAULT 'draft',
            approved_by          UUID,
            inv_transaction_ids  JSONB NOT NULL DEFAULT '[]'::jsonb,
            shipped_at           TIMESTAMPTZ,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_pur_return_code UNIQUE (tenant_id, return_code)
        )
    """)
    op.execute("CREATE INDEX idx_pur_return_order ON pur_purchase_return (tenant_id, order_id)")

    op.execute("""
        CREATE TABLE pur_purchase_return_line (
            line_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            return_id            UUID NOT NULL REFERENCES pur_purchase_return(return_id),
            order_line_id        UUID NOT NULL,
            sku_id               UUID NOT NULL,
            return_quantity      NUMERIC(18,6) NOT NULL,
            reason               VARCHAR(512) NOT NULL DEFAULT '',
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_pur_retline_return ON pur_purchase_return_line (tenant_id, return_id)")

    op.execute("""
        CREATE TABLE pur_purchase_settlement (
            settlement_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            settlement_code      VARCHAR(64) NOT NULL,
            order_id             UUID NOT NULL REFERENCES pur_purchase_order(order_id),
            supplier_id          UUID NOT NULL,
            total_amount         NUMERIC(18,6) NOT NULL DEFAULT 0,
            received_amount      NUMERIC(18,6) NOT NULL DEFAULT 0,
            diff_amount          NUMERIC(18,6) NOT NULL DEFAULT 0,
            status               VARCHAR(16) NOT NULL DEFAULT 'pending',
            inv_transaction_ids  JSONB NOT NULL DEFAULT '[]'::jsonb,
            reconciled_at        TIMESTAMPTZ,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_pur_settlement_code UNIQUE (tenant_id, settlement_code)
        )
    """)
    op.execute("CREATE INDEX idx_pur_settlement_order ON pur_purchase_settlement (tenant_id, order_id)")

    op.execute("""
        CREATE TABLE pur_invoice (
            invoice_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            invoice_code         VARCHAR(64) NOT NULL,
            supplier_id          UUID NOT NULL,
            settlement_id        UUID,
            invoice_amount       NUMERIC(18,6) NOT NULL DEFAULT 0,
            matched_amount       NUMERIC(18,6) NOT NULL DEFAULT 0,
            status               VARCHAR(16) NOT NULL DEFAULT 'draft',
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_pur_invoice_code UNIQUE (tenant_id, invoice_code)
        )
    """)
    op.execute("CREATE INDEX idx_pur_invoice_supplier ON pur_invoice (tenant_id, supplier_id)")

    op.execute("""
        CREATE TABLE pur_payment_request (
            payment_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            payment_code         VARCHAR(64) NOT NULL,
            settlement_id        UUID NOT NULL,
            supplier_id          UUID NOT NULL,
            amount               NUMERIC(18,6) NOT NULL DEFAULT 0,
            status               VARCHAR(16) NOT NULL DEFAULT 'pending',
            inv_transaction_ids  JSONB NOT NULL DEFAULT '[]'::jsonb,
            paid_at              TIMESTAMPTZ,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_pur_payment_code UNIQUE (tenant_id, payment_code)
        )
    """)
    op.execute("CREATE INDEX idx_pur_payment_settlement ON pur_payment_request (tenant_id, settlement_id)")

    op.execute("""
        CREATE TABLE pur_purchase_audit (
            audit_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            user_id              UUID NOT NULL,
            event_type           VARCHAR(64) NOT NULL,
            supplier_id          UUID,
            order_id             UUID,
            receipt_id           UUID,
            return_id            UUID,
            settlement_id        UUID,
            before_state         JSONB NOT NULL DEFAULT '{}'::jsonb,
            after_state          JSONB NOT NULL DEFAULT '{}'::jsonb,
            wms_receiving_id     UUID,
            inv_transaction_ids  JSONB NOT NULL DEFAULT '[]'::jsonb,
            reason               VARCHAR(512) NOT NULL DEFAULT '',
            operated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_pur_audit_tenant_event ON pur_purchase_audit (tenant_id, event_type)")

    op.execute("""
        CREATE TABLE pur_reconcile_diff (
            diff_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            order_id             UUID NOT NULL,
            sku_id               UUID NOT NULL,
            warehouse_id         UUID NOT NULL,
            pur_quantity         NUMERIC(18,6) NOT NULL,
            wms_quantity         NUMERIC(18,6) NOT NULL,
            inv_quantity         NUMERIC(18,6) NOT NULL,
            diff_type            VARCHAR(32) NOT NULL,
            status               VARCHAR(16) NOT NULL DEFAULT 'open',
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_pur_reconcile_diff_order ON pur_reconcile_diff (tenant_id, order_id)")


def downgrade() -> None:
    for tbl in [
        "pur_reconcile_diff", "pur_purchase_audit", "pur_payment_request",
        "pur_invoice", "pur_purchase_settlement", "pur_purchase_return_line",
        "pur_purchase_return", "pur_purchase_receipt_line", "pur_purchase_receipt",
        "pur_asn_line", "pur_asn", "pur_purchase_order_line", "pur_purchase_order",
        "pur_purchase_request_line", "pur_purchase_request", "pur_supplier_evaluation",
        "pur_quotation_line", "pur_quotation", "pur_supplier_scope", "pur_supplier",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")