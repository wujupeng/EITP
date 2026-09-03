"""FIN 资金池账户表 + 资金调拨表（含可用余额守恒 CHECK 约束）。

Revision ID: 077
Revises: 076
Create Date: 2026-09-03
"""

from __future__ import annotations

from alembic import op

revision = "077"
down_revision = "076"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE fin_treasury_account (
            account_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           UUID NOT NULL,
            account_no          VARCHAR(64) NOT NULL,
            account_type        VARCHAR(32) NOT NULL DEFAULT 'BANK',
            currency            VARCHAR(8) NOT NULL DEFAULT 'CNY',
            balance             NUMERIC(18,2) NOT NULL DEFAULT 0,
            frozen_amount       NUMERIC(18,2) NOT NULL DEFAULT 0,
            available_balance   NUMERIC(18,2) NOT NULL DEFAULT 0,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_fin_treasury_account_no UNIQUE (tenant_id, account_no),
            CONSTRAINT ck_fin_treasury_available CHECK (available_balance = balance - frozen_amount)
        )
    """)
    op.execute("CREATE INDEX idx_fin_treasury_account_tenant_type ON fin_treasury_account (tenant_id, account_type)")

    op.execute("""
        CREATE TABLE fin_treasury_transfer (
            transfer_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           UUID NOT NULL,
            transfer_no         VARCHAR(64) NOT NULL,
            from_account_id     UUID NOT NULL REFERENCES fin_treasury_account(account_id),
            to_account_id       UUID NOT NULL REFERENCES fin_treasury_account(account_id),
            transfer_amount     NUMERIC(18,2) NOT NULL DEFAULT 0,
            reason              TEXT,
            status              VARCHAR(32) NOT NULL DEFAULT 'PENDING_APPROVAL',
            approver_ids        JSONB NOT NULL DEFAULT '[]'::jsonb,
            approved_at         TIMESTAMPTZ,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_fin_treasury_transfer_no UNIQUE (transfer_no),
            CONSTRAINT ck_fin_treasury_transfer_diff_accounts CHECK (from_account_id <> to_account_id)
        )
    """)
    op.execute("CREATE INDEX idx_fin_treasury_transfer_tenant_status ON fin_treasury_transfer (tenant_id, status)")
    op.execute("CREATE INDEX idx_fin_treasury_transfer_from ON fin_treasury_transfer (tenant_id, from_account_id)")
    op.execute("CREATE INDEX idx_fin_treasury_transfer_to ON fin_treasury_transfer (tenant_id, to_account_id)")

    for tbl in ["fin_treasury_account", "fin_treasury_transfer"]:
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
    for tbl in ["fin_treasury_transfer", "fin_treasury_account"]:
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_platform_admin ON {tbl}")
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_tenant ON {tbl}")
        op.execute(f"ALTER TABLE {tbl} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY")

    op.execute("DROP INDEX IF EXISTS idx_fin_treasury_transfer_to")
    op.execute("DROP INDEX IF EXISTS idx_fin_treasury_transfer_from")
    op.execute("DROP INDEX IF EXISTS idx_fin_treasury_transfer_tenant_status")
    op.execute("DROP TABLE IF EXISTS fin_treasury_transfer CASCADE")
    op.execute("DROP INDEX IF EXISTS idx_fin_treasury_account_tenant_type")
    op.execute("DROP TABLE IF EXISTS fin_treasury_account CASCADE")