"""FIN 对账批次表 + 对账明细表 + 对账差异表 + 差异处理记录表（append-only）。

Revision ID: 074
Revises: 073
Create Date: 2026-09-03
"""

from __future__ import annotations

from alembic import op

revision = "074"
down_revision = "073"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE fin_reconciliation (
            recon_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id         UUID NOT NULL,
            recon_no          VARCHAR(64) NOT NULL,
            period_start      DATE NOT NULL,
            period_end        DATE NOT NULL,
            scope_type        VARCHAR(32) NOT NULL,
            scope_value       VARCHAR(128) NOT NULL,
            data_source       VARCHAR(32) NOT NULL DEFAULT 'BANK',
            status            VARCHAR(32) NOT NULL DEFAULT 'CREATED',
            system_amount     NUMERIC(18,2) NOT NULL DEFAULT 0,
            external_amount   NUMERIC(18,2) NOT NULL DEFAULT 0,
            matched_count     INTEGER NOT NULL DEFAULT 0,
            diff_count        INTEGER NOT NULL DEFAULT 0,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_fin_recon_no UNIQUE (recon_no),
            CONSTRAINT uq_fin_recon_period_scope UNIQUE (tenant_id, period_start, period_end, scope_type, scope_value)
        )
    """)
    op.execute("CREATE INDEX idx_fin_recon_tenant_status ON fin_reconciliation (tenant_id, status)")
    op.execute("CREATE INDEX idx_fin_recon_period ON fin_reconciliation (tenant_id, period_start, period_end)")

    op.execute("""
        CREATE TABLE fin_reconciliation_line (
            line_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id         UUID NOT NULL,
            recon_id          UUID NOT NULL REFERENCES fin_reconciliation(recon_id),
            system_record     JSONB NOT NULL DEFAULT '{}'::jsonb,
            external_record   JSONB NOT NULL DEFAULT '{}'::jsonb,
            match_result      VARCHAR(32) NOT NULL DEFAULT 'PENDING',
            created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_fin_recon_line_recon ON fin_reconciliation_line (tenant_id, recon_id)")

    op.execute("""
        CREATE TABLE fin_reconciliation_difference (
            diff_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id         UUID NOT NULL,
            recon_id          UUID NOT NULL REFERENCES fin_reconciliation(recon_id),
            diff_type         VARCHAR(32) NOT NULL DEFAULT 'AMOUNT_DIFF',
            diff_amount       NUMERIC(18,2) NOT NULL DEFAULT 0,
            handle_status     VARCHAR(32) NOT NULL DEFAULT 'PENDING',
            created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_fin_recon_diff_recon ON fin_reconciliation_difference (tenant_id, recon_id)")
    op.execute("CREATE INDEX idx_fin_recon_diff_status ON fin_reconciliation_difference (tenant_id, handle_status)")

    op.execute("""
        CREATE TABLE fin_recon_diff_handle_record (
            record_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id        UUID NOT NULL,
            diff_id          UUID NOT NULL REFERENCES fin_reconciliation_difference(diff_id),
            handle_action    VARCHAR(64) NOT NULL,
            handle_by        VARCHAR(64) NOT NULL,
            handle_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            before_amount    NUMERIC(18,2) NOT NULL DEFAULT 0,
            after_amount     NUMERIC(18,2) NOT NULL DEFAULT 0,
            evidence         TEXT,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_fin_recon_handle_diff ON fin_recon_diff_handle_record (tenant_id, diff_id)")

    op.execute("""
        CREATE OR REPLACE FUNCTION fin_reject_handle_record_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'EITP_FIN_RECON_HANDLE_RECORD_IMMUTABLE: append-only table cannot be modified';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_fin_recon_diff_handle_record_immutable
        BEFORE UPDATE OR DELETE ON fin_recon_diff_handle_record
        FOR EACH ROW EXECUTE FUNCTION fin_reject_handle_record_mutation()
    """)

    for tbl in ["fin_reconciliation", "fin_reconciliation_line", "fin_reconciliation_difference", "fin_recon_diff_handle_record"]:
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
    for tbl in ["fin_recon_diff_handle_record", "fin_reconciliation_difference", "fin_reconciliation_line", "fin_reconciliation"]:
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_platform_admin ON {tbl}")
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_tenant ON {tbl}")
        op.execute(f"ALTER TABLE {tbl} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY")

    op.execute("DROP TRIGGER IF EXISTS trg_fin_recon_diff_handle_record_immutable ON fin_recon_diff_handle_record")
    op.execute("DROP FUNCTION IF EXISTS fin_reject_handle_record_mutation()")

    op.execute("DROP INDEX IF EXISTS idx_fin_recon_handle_diff")
    op.execute("DROP TABLE IF EXISTS fin_recon_diff_handle_record CASCADE")
    op.execute("DROP INDEX IF EXISTS idx_fin_recon_diff_status")
    op.execute("DROP INDEX IF EXISTS idx_fin_recon_diff_recon")
    op.execute("DROP TABLE IF EXISTS fin_reconciliation_difference CASCADE")
    op.execute("DROP INDEX IF EXISTS idx_fin_recon_line_recon")
    op.execute("DROP TABLE IF EXISTS fin_reconciliation_line CASCADE")
    op.execute("DROP INDEX IF EXISTS idx_fin_recon_period")
    op.execute("DROP INDEX IF EXISTS idx_fin_recon_tenant_status")
    op.execute("DROP TABLE IF EXISTS fin_reconciliation CASCADE")