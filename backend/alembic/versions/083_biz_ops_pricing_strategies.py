"""BIZ-OPS 定价策略表。

Revision ID: 083
Revises: 082
Create Date: 2026-09-04
"""

from __future__ import annotations

from alembic import op

revision = "083"
down_revision = "082"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE biz_ops_pricing_strategies (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id     UUID NOT NULL,
            strategy_key  VARCHAR(100) NOT NULL,
            strategy_name VARCHAR(200) NOT NULL,
            strategy_type VARCHAR(30) NOT NULL,
            target_ref    VARCHAR(100) NOT NULL,
            price_config  VARCHAR(4000) NOT NULL DEFAULT '{}',
            scope_level   VARCHAR(20) NOT NULL DEFAULT 'tenant',
            scope_ref     VARCHAR(100),
            priority      INTEGER NOT NULL DEFAULT 100,
            effective_from TIMESTAMPTZ,
            effective_to   TIMESTAMPTZ,
            is_active     VARCHAR(5) NOT NULL DEFAULT 'true',
            version       INTEGER NOT NULL DEFAULT 1,
            description   VARCHAR(500),
            created_by    UUID,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_biz_ops_ps_tenant_strategy UNIQUE (tenant_id, strategy_key)
        )
    """)
    op.execute("""
        CREATE INDEX ix_biz_ops_ps_tenant_type_target_priority
        ON biz_ops_pricing_strategies (tenant_id, strategy_type, target_ref, priority)
    """)

    op.execute("""
        CREATE TABLE biz_ops_pricing_strategy_versions (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id     UUID NOT NULL,
            strategy_key  VARCHAR(100) NOT NULL,
            strategy_name VARCHAR(200) NOT NULL,
            strategy_type VARCHAR(30) NOT NULL,
            target_ref    VARCHAR(100) NOT NULL,
            price_config  VARCHAR(4000) NOT NULL DEFAULT '{}',
            scope_level   VARCHAR(20) NOT NULL DEFAULT 'tenant',
            scope_ref     VARCHAR(100),
            priority      INTEGER NOT NULL DEFAULT 100,
            effective_from TIMESTAMPTZ,
            effective_to   TIMESTAMPTZ,
            version       INTEGER NOT NULL,
            description   VARCHAR(500),
            created_by    UUID,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_biz_ops_psv_tenant_strategy_ver UNIQUE (tenant_id, strategy_key, version)
        )
    """)
    op.execute("""
        CREATE INDEX ix_biz_ops_psv_tenant_strategy
        ON biz_ops_pricing_strategy_versions (tenant_id, strategy_key)
    """)

    for table in ["biz_ops_pricing_strategies", "biz_ops_pricing_strategy_versions"]:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY rls_{table}_tenant ON {table} FOR ALL TO public
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """)


def downgrade() -> None:
    for table in ["biz_ops_pricing_strategy_versions", "biz_ops_pricing_strategies"]:
        op.execute(f"DROP POLICY IF EXISTS rls_{table}_tenant ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.execute("DROP INDEX IF EXISTS ix_biz_ops_psv_tenant_strategy")
    op.execute("DROP TABLE IF EXISTS biz_ops_pricing_strategy_versions CASCADE")
    op.execute("DROP INDEX IF EXISTS ix_biz_ops_ps_tenant_type_target_priority")
    op.execute("DROP TABLE IF EXISTS biz_ops_pricing_strategies CASCADE")