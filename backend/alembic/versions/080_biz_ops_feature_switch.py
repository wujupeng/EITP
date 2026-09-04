"""BIZ-OPS 功能开关表。

Revision ID: 080
Revises: 079
Create Date: 2026-09-03
"""

from __future__ import annotations

from alembic import op

revision = "080"
down_revision = "079"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE biz_ops_feature_switches (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           UUID NOT NULL,
            feature_key         VARCHAR(100) NOT NULL,
            scope               VARCHAR(20) NOT NULL,
            is_enabled          VARCHAR(5) NOT NULL DEFAULT 'true',
            parent_feature_key  VARCHAR(100),
            description         VARCHAR(500),
            updated_by          UUID,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_biz_ops_fs_tenant_feature UNIQUE (tenant_id, feature_key)
        )
    """)
    op.execute(
        "CREATE INDEX ix_biz_ops_fs_tenant_scope "
        "ON biz_ops_feature_switches (tenant_id, scope)"
    )

    op.execute("ALTER TABLE biz_ops_feature_switches ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE biz_ops_feature_switches FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY rls_biz_ops_fs_tenant ON biz_ops_feature_switches FOR ALL TO public
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS rls_biz_ops_fs_tenant ON biz_ops_feature_switches")
    op.execute("ALTER TABLE biz_ops_feature_switches NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE biz_ops_feature_switches DISABLE ROW LEVEL SECURITY")
    op.execute("DROP INDEX IF EXISTS ix_biz_ops_fs_tenant_scope")
    op.execute("DROP TABLE IF EXISTS biz_ops_feature_switches CASCADE")