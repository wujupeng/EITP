"""FIN 结算单表 + 结算明细表 + 跨租户结算 RLS 互访策略。

Revision ID: 070
Revises: 069
Create Date: 2026-09-03
"""

from __future__ import annotations

from alembic import op

revision = "070"
down_revision = "069"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE fin_settlement (
            settlement_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            settlement_no        VARCHAR(64) NOT NULL,
            settlement_type      VARCHAR(32) NOT NULL DEFAULT 'PURCHASE',
            status               VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
            counterparty_id      VARCHAR(128) NOT NULL,
            counterparty_type    VARCHAR(32) NOT NULL DEFAULT 'SUPPLIER',
            settlement_amount    NUMERIC(18,2) NOT NULL DEFAULT 0,
            tax_amount           NUMERIC(18,2) NOT NULL DEFAULT 0,
            currency             VARCHAR(8) NOT NULL DEFAULT 'CNY',
            initiator_tenant_id  UUID NOT NULL,
            receiver_tenant_id   UUID,
            related_order_type   VARCHAR(32),
            related_order_id     VARCHAR(128),
            confirmed_at         TIMESTAMPTZ,
            settled_at           TIMESTAMPTZ,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_fin_settlement_no UNIQUE (settlement_no),
            CONSTRAINT uq_fin_settlement_tenant_no UNIQUE (tenant_id, settlement_no)
        )
    """)
    op.execute("CREATE INDEX idx_fin_settlement_tenant_status ON fin_settlement (tenant_id, status)")
    op.execute("CREATE INDEX idx_fin_settlement_type ON fin_settlement (settlement_type)")
    op.execute("CREATE INDEX idx_fin_settlement_counterparty ON fin_settlement (tenant_id, counterparty_id)")
    op.execute("CREATE INDEX idx_fin_settlement_cross_tenant ON fin_settlement (initiator_tenant_id, receiver_tenant_id)")

    op.execute("""
        CREATE TABLE fin_settlement_line (
            line_id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id                UUID NOT NULL,
            settlement_id            UUID NOT NULL REFERENCES fin_settlement(settlement_id),
            line_no                  INTEGER NOT NULL,
            product_ref              VARCHAR(128) NOT NULL,
            quantity                 NUMERIC(18,4) NOT NULL DEFAULT 0,
            tax_inclusive_unit_price NUMERIC(18,2) NOT NULL DEFAULT 0,
            tax_rate                 NUMERIC(6,4) NOT NULL DEFAULT 0,
            tax_amount               NUMERIC(18,2) NOT NULL DEFAULT 0,
            line_amount              NUMERIC(18,2) NOT NULL DEFAULT 0,
            created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_fin_settlement_line_no UNIQUE (settlement_id, line_no)
        )
    """)
    op.execute("CREATE INDEX idx_fin_settlement_line_settlement ON fin_settlement_line (tenant_id, settlement_id)")

    op.execute("ALTER TABLE fin_settlement ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE fin_settlement FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY rls_fin_settlement_tenant ON fin_settlement FOR ALL TO public
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)
    op.execute("""
        CREATE POLICY rls_fin_settlement_cross_tenant ON fin_settlement FOR SELECT TO public
        USING (
            initiator_tenant_id = current_setting('app.tenant_id', true)::uuid
            OR receiver_tenant_id = current_setting('app.tenant_id', true)::uuid
            OR current_setting('app.is_platform_admin', true) = 'true'
        )
    """)
    op.execute("""
        CREATE POLICY rls_fin_settlement_platform_admin ON fin_settlement FOR ALL TO public
        USING (current_setting('app.is_platform_admin', true) = 'true')
        WITH CHECK (current_setting('app.is_platform_admin', true) = 'true')
    """)

    op.execute("ALTER TABLE fin_settlement_line ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE fin_settlement_line FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY rls_fin_settlement_line_tenant ON fin_settlement_line FOR ALL TO public
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)
    op.execute("""
        CREATE POLICY rls_fin_settlement_line_platform_admin ON fin_settlement_line FOR ALL TO public
        USING (current_setting('app.is_platform_admin', true) = 'true')
        WITH CHECK (current_setting('app.is_platform_admin', true) = 'true')
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS rls_fin_settlement_line_platform_admin ON fin_settlement_line")
    op.execute("DROP POLICY IF EXISTS rls_fin_settlement_line_tenant ON fin_settlement_line")
    op.execute("ALTER TABLE fin_settlement_line NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE fin_settlement_line DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS rls_fin_settlement_platform_admin ON fin_settlement")
    op.execute("DROP POLICY IF EXISTS rls_fin_settlement_cross_tenant ON fin_settlement")
    op.execute("DROP POLICY IF EXISTS rls_fin_settlement_tenant ON fin_settlement")
    op.execute("ALTER TABLE fin_settlement NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE fin_settlement DISABLE ROW LEVEL SECURITY")

    op.execute("DROP INDEX IF EXISTS idx_fin_settlement_line_settlement")
    op.execute("DROP TABLE IF EXISTS fin_settlement_line CASCADE")

    op.execute("DROP INDEX IF EXISTS idx_fin_settlement_cross_tenant")
    op.execute("DROP INDEX IF EXISTS idx_fin_settlement_counterparty")
    op.execute("DROP INDEX IF EXISTS idx_fin_settlement_type")
    op.execute("DROP INDEX IF EXISTS idx_fin_settlement_tenant_status")
    op.execute("DROP TABLE IF EXISTS fin_settlement CASCADE")