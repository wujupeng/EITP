"""FIN 总账科目表 + 总账凭证表 + 总账凭证行表 + 已结账期间 append-only 触发器。

Revision ID: 076
Revises: 075
Create Date: 2026-09-03
"""

from __future__ import annotations

from alembic import op

revision = "076"
down_revision = "075"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE fin_gl_account (
            account_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           UUID NOT NULL,
            account_code        VARCHAR(64) NOT NULL,
            account_name        VARCHAR(256) NOT NULL,
            category            VARCHAR(32) NOT NULL DEFAULT 'ASSET',
            balance_direction   VARCHAR(8) NOT NULL DEFAULT 'DEBIT',
            parent_code         VARCHAR(64),
            opening_balance     NUMERIC(18,2) NOT NULL DEFAULT 0,
            period_debit        NUMERIC(18,2) NOT NULL DEFAULT 0,
            period_credit       NUMERIC(18,2) NOT NULL DEFAULT 0,
            closing_balance     NUMERIC(18,2) NOT NULL DEFAULT 0,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_fin_gl_account_code UNIQUE (tenant_id, account_code)
        )
    """)
    op.execute("CREATE INDEX idx_fin_gl_account_tenant_category ON fin_gl_account (tenant_id, category)")
    op.execute("CREATE INDEX idx_fin_gl_account_parent ON fin_gl_account (tenant_id, parent_code)")

    op.execute("""
        CREATE TABLE fin_gl_voucher (
            gl_voucher_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id               UUID NOT NULL,
            voucher_no              VARCHAR(64) NOT NULL,
            voucher_date            DATE NOT NULL,
            summary                 TEXT,
            business_ref_type       VARCHAR(32),
            business_ref_id         VARCHAR(128),
            red_original_voucher_no VARCHAR(64),
            period                  VARCHAR(16) NOT NULL,
            is_period_closed        BOOLEAN NOT NULL DEFAULT FALSE,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_fin_gl_voucher_no_period UNIQUE (tenant_id, voucher_no, period)
        )
    """)
    op.execute("CREATE INDEX idx_fin_gl_voucher_tenant_period ON fin_gl_voucher (tenant_id, period)")
    op.execute("CREATE INDEX idx_fin_gl_voucher_tenant_date ON fin_gl_voucher (tenant_id, voucher_date)")
    op.execute("CREATE INDEX idx_fin_gl_voucher_business_ref ON fin_gl_voucher (tenant_id, business_ref_type, business_ref_id)")

    op.execute("""
        CREATE OR REPLACE FUNCTION fin_reject_gl_period_closed_mutation() RETURNS trigger AS $$
        BEGIN
            IF OLD.is_period_closed = TRUE THEN
                RAISE EXCEPTION 'EITP_FIN_GL_PERIOD_CLOSED_IMMUTABLE: closed period voucher cannot be modified';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_fin_gl_voucher_period_closed_immutable
        BEFORE UPDATE OR DELETE ON fin_gl_voucher
        FOR EACH ROW EXECUTE FUNCTION fin_reject_gl_period_closed_mutation()
    """)

    op.execute("""
        CREATE TABLE fin_gl_voucher_line (
            line_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            gl_voucher_id        UUID NOT NULL REFERENCES fin_gl_voucher(gl_voucher_id),
            line_no              INTEGER NOT NULL,
            account_code         VARCHAR(64) NOT NULL,
            debit_amount         NUMERIC(18,2) NOT NULL DEFAULT 0,
            credit_amount        NUMERIC(18,2) NOT NULL DEFAULT 0,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_fin_gl_voucher_line_no UNIQUE (gl_voucher_id, line_no)
        )
    """)
    op.execute("CREATE INDEX idx_fin_gl_voucher_line_voucher ON fin_gl_voucher_line (tenant_id, gl_voucher_id)")
    op.execute("CREATE INDEX idx_fin_gl_voucher_line_account ON fin_gl_voucher_line (tenant_id, account_code)")

    for tbl in ["fin_gl_account", "fin_gl_voucher", "fin_gl_voucher_line"]:
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
    for tbl in ["fin_gl_voucher_line", "fin_gl_voucher", "fin_gl_account"]:
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_platform_admin ON {tbl}")
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_tenant ON {tbl}")
        op.execute(f"ALTER TABLE {tbl} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY")

    op.execute("DROP INDEX IF EXISTS idx_fin_gl_voucher_line_account")
    op.execute("DROP INDEX IF EXISTS idx_fin_gl_voucher_line_voucher")
    op.execute("DROP TABLE IF EXISTS fin_gl_voucher_line CASCADE")

    op.execute("DROP TRIGGER IF EXISTS trg_fin_gl_voucher_period_closed_immutable ON fin_gl_voucher")
    op.execute("DROP FUNCTION IF EXISTS fin_reject_gl_period_closed_mutation()")
    op.execute("DROP INDEX IF EXISTS idx_fin_gl_voucher_business_ref")
    op.execute("DROP INDEX IF EXISTS idx_fin_gl_voucher_tenant_date")
    op.execute("DROP INDEX IF EXISTS idx_fin_gl_voucher_tenant_period")
    op.execute("DROP TABLE IF EXISTS fin_gl_voucher CASCADE")

    op.execute("DROP INDEX IF EXISTS idx_fin_gl_account_parent")
    op.execute("DROP INDEX IF EXISTS idx_fin_gl_account_tenant_category")
    op.execute("DROP TABLE IF EXISTS fin_gl_account CASCADE")