"""FIN 应收应付凭证表（含金额守恒 CHECK 约束）。

Revision ID: 075
Revises: 074
Create Date: 2026-09-03
"""

from __future__ import annotations

from alembic import op

revision = "075"
down_revision = "074"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE fin_ar_voucher (
            voucher_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           UUID NOT NULL,
            voucher_no          VARCHAR(64) NOT NULL,
            business_ref_type   VARCHAR(32) NOT NULL,
            business_ref_id     VARCHAR(128) NOT NULL,
            receivable_amount   NUMERIC(18,2) NOT NULL DEFAULT 0,
            received_amount     NUMERIC(18,2) NOT NULL DEFAULT 0,
            unreceived_amount   NUMERIC(18,2) NOT NULL DEFAULT 0,
            status              VARCHAR(32) NOT NULL DEFAULT 'OPEN',
            credit_period_days  INTEGER NOT NULL DEFAULT 30,
            due_date            DATE,
            is_overdue          BOOLEAN NOT NULL DEFAULT FALSE,
            overdue_days        INTEGER NOT NULL DEFAULT 0,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_fin_ar_voucher_no UNIQUE (voucher_no),
            CONSTRAINT ck_fin_ar_amount_conserved CHECK (receivable_amount = received_amount + unreceived_amount)
        )
    """)
    op.execute("CREATE INDEX idx_fin_ar_tenant_status ON fin_ar_voucher (tenant_id, status)")
    op.execute("CREATE INDEX idx_fin_ar_business_ref ON fin_ar_voucher (tenant_id, business_ref_type, business_ref_id)")
    op.execute("CREATE INDEX idx_fin_ar_overdue ON fin_ar_voucher (tenant_id, is_overdue) WHERE is_overdue = TRUE")
    op.execute("CREATE INDEX idx_fin_ar_due_date ON fin_ar_voucher (tenant_id, due_date)")

    op.execute("""
        CREATE TABLE fin_ap_voucher (
            voucher_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           UUID NOT NULL,
            voucher_no          VARCHAR(64) NOT NULL,
            business_ref_type   VARCHAR(32) NOT NULL,
            business_ref_id     VARCHAR(128) NOT NULL,
            payable_amount      NUMERIC(18,2) NOT NULL DEFAULT 0,
            paid_amount         NUMERIC(18,2) NOT NULL DEFAULT 0,
            unpaid_amount       NUMERIC(18,2) NOT NULL DEFAULT 0,
            status              VARCHAR(32) NOT NULL DEFAULT 'OPEN',
            payment_terms       VARCHAR(64),
            due_date            DATE,
            is_overdue          BOOLEAN NOT NULL DEFAULT FALSE,
            overdue_days        INTEGER NOT NULL DEFAULT 0,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_fin_ap_voucher_no UNIQUE (voucher_no),
            CONSTRAINT ck_fin_ap_amount_conserved CHECK (payable_amount = paid_amount + unpaid_amount)
        )
    """)
    op.execute("CREATE INDEX idx_fin_ap_tenant_status ON fin_ap_voucher (tenant_id, status)")
    op.execute("CREATE INDEX idx_fin_ap_business_ref ON fin_ap_voucher (tenant_id, business_ref_type, business_ref_id)")
    op.execute("CREATE INDEX idx_fin_ap_overdue ON fin_ap_voucher (tenant_id, is_overdue) WHERE is_overdue = TRUE")
    op.execute("CREATE INDEX idx_fin_ap_due_date ON fin_ap_voucher (tenant_id, due_date)")

    for tbl in ["fin_ar_voucher", "fin_ap_voucher"]:
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
    for tbl in ["fin_ap_voucher", "fin_ar_voucher"]:
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_platform_admin ON {tbl}")
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_tenant ON {tbl}")
        op.execute(f"ALTER TABLE {tbl} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY")

    op.execute("DROP INDEX IF EXISTS idx_fin_ap_due_date")
    op.execute("DROP INDEX IF EXISTS idx_fin_ap_overdue")
    op.execute("DROP INDEX IF EXISTS idx_fin_ap_business_ref")
    op.execute("DROP INDEX IF EXISTS idx_fin_ap_tenant_status")
    op.execute("DROP TABLE IF EXISTS fin_ap_voucher CASCADE")
    op.execute("DROP INDEX IF EXISTS idx_fin_ar_due_date")
    op.execute("DROP INDEX IF EXISTS idx_fin_ar_overdue")
    op.execute("DROP INDEX IF EXISTS idx_fin_ar_business_ref")
    op.execute("DROP INDEX IF EXISTS idx_fin_ar_tenant_status")
    op.execute("DROP TABLE IF EXISTS fin_ar_voucher CASCADE")