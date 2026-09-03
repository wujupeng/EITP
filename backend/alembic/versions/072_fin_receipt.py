"""FIN 收款单表 + 收款核销明细表。

Revision ID: 072
Revises: 071
Create Date: 2026-09-03
"""

from __future__ import annotations

from alembic import op

revision = "072"
down_revision = "071"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE fin_receipt (
            receipt_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            receipt_no           VARCHAR(64) NOT NULL,
            receipt_amount       NUMERIC(18,2) NOT NULL DEFAULT 0,
            receiver_account     TEXT NOT NULL DEFAULT '',
            payer_account        TEXT NOT NULL DEFAULT '',
            bank_ref             VARCHAR(128) NOT NULL,
            status               VARCHAR(32) NOT NULL DEFAULT 'PENDING_CONFIRM',
            arrival_time         TIMESTAMPTZ,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_fin_receipt_no UNIQUE (receipt_no),
            CONSTRAINT uq_fin_receipt_bank_ref UNIQUE (bank_ref)
        )
    """)
    op.execute("CREATE INDEX idx_fin_receipt_tenant_status ON fin_receipt (tenant_id, status)")
    op.execute("CREATE INDEX idx_fin_receipt_bank_ref ON fin_receipt (bank_ref)")

    op.execute("""
        CREATE TABLE fin_receipt_writeoff_line (
            line_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           UUID NOT NULL,
            receipt_id          UUID NOT NULL REFERENCES fin_receipt(receipt_id),
            ar_voucher_no       VARCHAR(64) NOT NULL,
            write_off_amount    NUMERIC(18,2) NOT NULL DEFAULT 0,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_fin_receipt_writeoff UNIQUE (receipt_id, ar_voucher_no)
        )
    """)
    op.execute("CREATE INDEX idx_fin_receipt_writeoff_receipt ON fin_receipt_writeoff_line (tenant_id, receipt_id)")
    op.execute("CREATE INDEX idx_fin_receipt_writeoff_ar ON fin_receipt_writeoff_line (tenant_id, ar_voucher_no)")

    for tbl in ["fin_receipt", "fin_receipt_writeoff_line"]:
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
    for tbl in ["fin_receipt_writeoff_line", "fin_receipt"]:
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_platform_admin ON {tbl}")
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_tenant ON {tbl}")
        op.execute(f"ALTER TABLE {tbl} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY")

    op.execute("DROP INDEX IF EXISTS idx_fin_receipt_writeoff_ar")
    op.execute("DROP INDEX IF EXISTS idx_fin_receipt_writeoff_receipt")
    op.execute("DROP TABLE IF EXISTS fin_receipt_writeoff_line CASCADE")
    op.execute("DROP INDEX IF EXISTS idx_fin_receipt_bank_ref")
    op.execute("DROP INDEX IF EXISTS idx_fin_receipt_tenant_status")
    op.execute("DROP TABLE IF EXISTS fin_receipt CASCADE")