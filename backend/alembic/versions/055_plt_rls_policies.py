"""PLT RLS 策略。

Revision ID: 055
Revises: 054
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op

revision = "055"
down_revision = "054"
branch_labels = None
depends_on = None

_RLS_TABLES = [
    "plt_permission_matrix",
    "plt_menu_tree",
    "plt_permission_approval",
    "plt_tenant_quota",
    "plt_job_definition",
    "plt_api_version_contract",
    "plt_rate_limit_config",
    "plt_config_revision",
]


def upgrade() -> None:
    op.execute("ALTER TABLE plt_audit_record ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY rls_plt_audit_tenant ON plt_audit_record FOR ALL TO public
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)

    for tbl in _RLS_TABLES:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY rls_{tbl}_tenant ON {tbl} FOR ALL TO public
            USING (
                tenant_id = current_setting('app.current_tenant_id', true)::uuid
                OR current_setting('app.is_platform_admin', true) = 'true'
            )
            WITH CHECK (
                tenant_id = current_setting('app.current_tenant_id', true)::uuid
                OR current_setting('app.is_platform_admin', true) = 'true'
            )
        """)


def downgrade() -> None:
    for tbl in _RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_tenant ON {tbl}")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS rls_plt_audit_tenant ON plt_audit_record")
    op.execute("ALTER TABLE plt_audit_record DISABLE ROW LEVEL SECURITY")