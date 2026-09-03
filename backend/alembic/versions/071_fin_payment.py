"""FIN 付款单表。

Revision ID: 071
Revises: 070
Create Date: 2026-09-03
"""

from __future__ import annotations

from alembic import op

revision = "071"
down_revision = "070"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE fin_payment (
            payment_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            payment_no           VARCHAR(64) NOT NULL,
            ap_voucher_no        VARCHAR(64),
            payment_amount       NUMERIC(18,2) NOT NULL DEFAULT 0,
            payment_method       VARCHAR(32) NOT NULL DEFAULT 'BANK_TRANSFER',
            payment_account      TEXT NOT NULL DEFAULT '',
            payee_account        TEXT NOT NULL DEFAULT '',
            status               VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
            approver_id          VARCHAR(64),
            approval_opinion     TEXT,
            approved_at          TIMESTAMPTZ,
            bank_ref             VARCHAR(128),
            expected_payment_date DATE,
            actual_payment_date  DATE,
            fail_reason          TEXT,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_fin_payment_no UNIQUE (payment_no),
            CONSTRAINT uq_fin_payment_bank_ref UNIQUE (bank_ref)
        )
    """)
    op.execute("CREATE INDEX idx_fin_payment_tenant_status ON fin_payment (tenant_id, status)")
    op.execute("CREATE INDEX idx_fin_payment_ap_voucher ON fin_payment (tenant_id, ap_voucher_no)")
    op.execute("CREATE INDEX idx_fin_payment_bank_ref ON fin_payment (bank_ref) WHERE bank_ref IS NOT NULL")

    op.execute("ALTER TABLE fin_payment ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE fin_payment FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY rls_fin_payment_tenant ON fin_payment FOR ALL TO public
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)
    op.execute("""
        CREATE POLICY rls_fin_payment_platform_admin ON fin_payment FOR ALL TO public
        USING (current_setting('app.is_platform_admin', true) = 'true')
        WITH CHECK (current_setting('app.is_platform_admin', true) = 'true')
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS rls_fin_payment_platform_admin ON fin_payment")
    op.execute("DROP POLICY IF EXISTS rls_fin_payment_tenant ON fin_payment")
    op.execute("ALTER TABLE fin_payment NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE fin_payment DISABLE ROW LEVEL SECURITY")
    op.execute("DROP INDEX IF EXISTS idx_fin_payment_bank_ref")
    op.execute("DROP INDEX IF EXISTS idx_fin_payment_ap_voucher")
    op.execute("DROP INDEX IF EXISTS idx_fin_payment_tenant_status")
    op.execute("DROP TABLE IF EXISTS fin_payment CASCADE")