"""FIN 发票表 + 发票明细表 + 归档 append-only 触发器。

Revision ID: 073
Revises: 072
Create Date: 2026-09-03
"""

from __future__ import annotations

from alembic import op

revision = "073"
down_revision = "072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE fin_invoice (
            invoice_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id               UUID NOT NULL,
            invoice_code            VARCHAR(64) NOT NULL,
            invoice_no              VARCHAR(64) NOT NULL,
            invoice_type            VARCHAR(32) NOT NULL DEFAULT 'VAT_NORMAL',
            status                  VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
            buyer_info              JSONB NOT NULL DEFAULT '{}'::jsonb,
            seller_info             JSONB NOT NULL DEFAULT '{}'::jsonb,
            tax_exclusive_amount    NUMERIC(18,2) NOT NULL DEFAULT 0,
            tax_amount              NUMERIC(18,2) NOT NULL DEFAULT 0,
            tax_inclusive_amount    NUMERIC(18,2) NOT NULL DEFAULT 0,
            red_original_invoice_no VARCHAR(64),
            archive_hash            CHAR(64),
            image_storage_id        VARCHAR(256),
            invoice_date            DATE NOT NULL,
            void_reason             TEXT,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_fin_invoice_code_no UNIQUE (invoice_code, invoice_no),
            CONSTRAINT uq_fin_invoice_tenant_code_no UNIQUE (tenant_id, invoice_code, invoice_no)
        )
    """)
    op.execute("CREATE INDEX idx_fin_invoice_tenant_status ON fin_invoice (tenant_id, status)")
    op.execute("CREATE INDEX idx_fin_invoice_type ON fin_invoice (tenant_id, invoice_type)")
    op.execute("CREATE INDEX idx_fin_invoice_date ON fin_invoice (tenant_id, invoice_date)")

    op.execute("""
        CREATE OR REPLACE FUNCTION fin_reject_invoice_archived_mutation() RETURNS trigger AS $$
        BEGIN
            IF OLD.status = 'ARCHIVED' THEN
                RAISE EXCEPTION 'EITP_FIN_INVOICE_ARCHIVED_IMMUTABLE: archived invoice cannot be modified';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_fin_invoice_archived_immutable
        BEFORE UPDATE OR DELETE ON fin_invoice
        FOR EACH ROW EXECUTE FUNCTION fin_reject_invoice_archived_mutation()
    """)

    op.execute("""
        CREATE TABLE fin_invoice_line (
            line_id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id                UUID NOT NULL,
            invoice_id               UUID NOT NULL REFERENCES fin_invoice(invoice_id),
            line_no                  INTEGER NOT NULL,
            product_name             VARCHAR(256) NOT NULL DEFAULT '',
            spec                     VARCHAR(256) NOT NULL DEFAULT '',
            quantity                 NUMERIC(18,4) NOT NULL DEFAULT 0,
            tax_exclusive_unit_price NUMERIC(18,2) NOT NULL DEFAULT 0,
            tax_rate                 NUMERIC(6,4) NOT NULL DEFAULT 0,
            tax_exclusive_amount     NUMERIC(18,2) NOT NULL DEFAULT 0,
            tax_amount               NUMERIC(18,2) NOT NULL DEFAULT 0,
            tax_inclusive_amount     NUMERIC(18,2) NOT NULL DEFAULT 0,
            created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_fin_invoice_line_no UNIQUE (invoice_id, line_no)
        )
    """)
    op.execute("CREATE INDEX idx_fin_invoice_line_invoice ON fin_invoice_line (tenant_id, invoice_id)")

    for tbl in ["fin_invoice", "fin_invoice_line"]:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY rls_{tbl}_tenant ON {tbl} FOR ALL TO public
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """)
        op.execute(f"""
            CREATE POLICY rls_{tbl}_platform_admin ON {tbl} FOR ALL TO public
            USING (current_setting('app.is_platform_admin', true) = 'true')
            WITH CHECK (current_setting('app.is_platform_admin', true) = 'true')
        """)


def downgrade() -> None:
    for tbl in ["fin_invoice_line", "fin_invoice"]:
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_platform_admin ON {tbl}")
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_tenant ON {tbl}")
        op.execute(f"ALTER TABLE {tbl} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY")

    op.execute("DROP INDEX IF EXISTS idx_fin_invoice_line_invoice")
    op.execute("DROP TABLE IF EXISTS fin_invoice_line CASCADE")

    op.execute("DROP TRIGGER IF EXISTS trg_fin_invoice_archived_immutable ON fin_invoice")
    op.execute("DROP FUNCTION IF EXISTS fin_reject_invoice_archived_mutation()")
    op.execute("DROP INDEX IF EXISTS idx_fin_invoice_date")
    op.execute("DROP INDEX IF EXISTS idx_fin_invoice_type")
    op.execute("DROP INDEX IF EXISTS idx_fin_invoice_tenant_status")
    op.execute("DROP TABLE IF EXISTS fin_invoice CASCADE")