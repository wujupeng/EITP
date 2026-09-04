"""BIZ-OPS 税务配置 + 库存策略表。

Revision ID: 084
Revises: 083
Create Date: 2026-09-04
"""

from __future__ import annotations

from alembic import op

revision = "084"
down_revision = "083"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE biz_ops_tax_configs (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id    UUID NOT NULL,
            config_key   VARCHAR(100) NOT NULL,
            config_name  VARCHAR(200) NOT NULL,
            tax_rates    VARCHAR(4000) NOT NULL DEFAULT '[]',
            tax_flag     VARCHAR(20) NOT NULL DEFAULT 'tax_exclusive',
            direction    VARCHAR(10) NOT NULL DEFAULT 'output',
            scope_level  VARCHAR(20) NOT NULL DEFAULT 'tenant',
            scope_ref    VARCHAR(100),
            special_rules VARCHAR(2000) NOT NULL DEFAULT '[]',
            is_active    VARCHAR(5) NOT NULL DEFAULT 'true',
            version      INTEGER NOT NULL DEFAULT 1,
            description  VARCHAR(500),
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_biz_ops_tc_tenant_config UNIQUE (tenant_id, config_key)
        )
    """)
    op.execute("CREATE INDEX ix_biz_ops_tc_tenant_scope ON biz_ops_tax_configs (tenant_id, scope_level)")

    op.execute("""
        CREATE TABLE biz_ops_inventory_strategies (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID NOT NULL,
            strategy_key    VARCHAR(100) NOT NULL,
            strategy_name   VARCHAR(200) NOT NULL,
            strategy_type   VARCHAR(20) NOT NULL,
            target_ref      VARCHAR(100) NOT NULL,
            threshold_config VARCHAR(4000) NOT NULL DEFAULT '{}',
            action_config   VARCHAR(2000) NOT NULL DEFAULT '{}',
            scope_level     VARCHAR(20) NOT NULL DEFAULT 'tenant',
            scope_ref       VARCHAR(100),
            priority        INTEGER NOT NULL DEFAULT 100,
            is_active       VARCHAR(5) NOT NULL DEFAULT 'true',
            version         INTEGER NOT NULL DEFAULT 1,
            description     VARCHAR(500),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_biz_ops_is_tenant_strategy UNIQUE (tenant_id, strategy_key)
        )
    """)
    op.execute("CREATE INDEX ix_biz_ops_is_tenant_type_target ON biz_ops_inventory_strategies (tenant_id, strategy_type, target_ref)")

    op.execute("""
        CREATE TABLE biz_ops_inventory_strategy_versions (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID NOT NULL,
            strategy_key    VARCHAR(100) NOT NULL,
            strategy_name   VARCHAR(200) NOT NULL,
            strategy_type   VARCHAR(20) NOT NULL,
            target_ref      VARCHAR(100) NOT NULL,
            threshold_config VARCHAR(4000) NOT NULL DEFAULT '{}',
            action_config   VARCHAR(2000) NOT NULL DEFAULT '{}',
            scope_level     VARCHAR(20) NOT NULL DEFAULT 'tenant',
            scope_ref       VARCHAR(100),
            priority        INTEGER NOT NULL DEFAULT 100,
            version         INTEGER NOT NULL,
            description     VARCHAR(500),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_biz_ops_isv_tenant_strategy_ver UNIQUE (tenant_id, strategy_key, version)
        )
    """)
    op.execute("CREATE INDEX ix_biz_ops_isv_tenant_strategy ON biz_ops_inventory_strategy_versions (tenant_id, strategy_key)")

    for table in ["biz_ops_tax_configs", "biz_ops_inventory_strategies", "biz_ops_inventory_strategy_versions"]:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY rls_{table}_tenant ON {table} FOR ALL TO public
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """)


def downgrade() -> None:
    for table in ["biz_ops_inventory_strategy_versions", "biz_ops_inventory_strategies", "biz_ops_tax_configs"]:
        op.execute(f"DROP POLICY IF EXISTS rls_{table}_tenant ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.execute("DROP INDEX IF EXISTS ix_biz_ops_isv_tenant_strategy")
    op.execute("DROP TABLE IF EXISTS biz_ops_inventory_strategy_versions CASCADE")
    op.execute("DROP INDEX IF EXISTS ix_biz_ops_is_tenant_type_target")
    op.execute("DROP TABLE IF EXISTS biz_ops_inventory_strategies CASCADE")
    op.execute("DROP INDEX IF EXISTS ix_biz_ops_tc_tenant_scope")
    op.execute("DROP TABLE IF EXISTS biz_ops_tax_configs CASCADE")