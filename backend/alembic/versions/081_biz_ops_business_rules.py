"""BIZ-OPS 业务规则表。

Revision ID: 081
Revises: 080
Create Date: 2026-09-03
"""

from __future__ import annotations

from alembic import op

revision = "081"
down_revision = "080"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE biz_ops_business_rules (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID NOT NULL,
            rule_key        VARCHAR(100) NOT NULL,
            rule_name       VARCHAR(200) NOT NULL,
            rule_type       VARCHAR(20) NOT NULL,
            trigger_point   VARCHAR(100) NOT NULL,
            expression      VARCHAR(2000) NOT NULL,
            priority        INTEGER NOT NULL DEFAULT 100,
            scope_level     VARCHAR(20) NOT NULL DEFAULT 'tenant',
            scope_ref       VARCHAR(100),
            action          VARCHAR(20),
            is_active       VARCHAR(5) NOT NULL DEFAULT 'true',
            version         INTEGER NOT NULL DEFAULT 1,
            description     VARCHAR(500),
            created_by      UUID,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_biz_ops_br_tenant_rule UNIQUE (tenant_id, rule_key)
        )
    """)
    op.execute("CREATE INDEX ix_biz_ops_br_tenant_trigger ON biz_ops_business_rules (tenant_id, trigger_point, is_active)")

    op.execute("""
        CREATE TABLE biz_ops_business_rule_versions (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID NOT NULL,
            rule_key        VARCHAR(100) NOT NULL,
            rule_name       VARCHAR(200) NOT NULL,
            rule_type       VARCHAR(20) NOT NULL,
            trigger_point   VARCHAR(100) NOT NULL,
            expression      VARCHAR(2000) NOT NULL,
            priority        INTEGER NOT NULL DEFAULT 100,
            scope_level     VARCHAR(20) NOT NULL DEFAULT 'tenant',
            scope_ref       VARCHAR(100),
            action          VARCHAR(20),
            version         INTEGER NOT NULL,
            description     VARCHAR(500),
            created_by      UUID,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_biz_ops_brv_tenant_rule_ver UNIQUE (tenant_id, rule_key, version)
        )
    """)
    op.execute("CREATE INDEX ix_biz_ops_brv_tenant_rule ON biz_ops_business_rule_versions (tenant_id, rule_key)")

    for table in ["biz_ops_business_rules", "biz_ops_business_rule_versions"]:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY rls_{table}_tenant ON {table} FOR ALL TO public
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """)


def downgrade() -> None:
    for table in ["biz_ops_business_rule_versions", "biz_ops_business_rules"]:
        op.execute(f"DROP POLICY IF EXISTS rls_{table}_tenant ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.execute("DROP INDEX IF EXISTS ix_biz_ops_brv_tenant_rule")
    op.execute("DROP TABLE IF EXISTS biz_ops_business_rule_versions CASCADE")
    op.execute("DROP INDEX IF EXISTS ix_biz_ops_br_tenant_trigger")
    op.execute("DROP TABLE IF EXISTS biz_ops_business_rules CASCADE")