"""SEC RLS 策略 - 审计表按租户隔离，元数据表平台管理员豁免。

Revision ID: 047
Revises: 046
Create Date: 2026-09-01
"""

from __future__ import annotations

from alembic import op

revision = "047"
down_revision = "046"
branch_labels = None
depends_on = None

_RLS_TENANT_TABLES = [
    "sec_certification_audit",
    "sec_platform_admin_access_log",
]

_RLS_PLATFORM_EXEMPT_TABLES = [
    "sec_certification_batch",
    "sec_certification_item",
    "sec_certification_report",
    "sec_certification_certificate",
    "sec_certification_config",
    "sec_platform_admin_access_request",
    "sec_redis_key_violation",
]


def upgrade() -> None:
    for tbl in _RLS_TENANT_TABLES:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY rls_{tbl}_tenant ON {tbl}
            FOR ALL TO public
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
        """)

    for tbl in _RLS_PLATFORM_EXEMPT_TABLES:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY rls_{tbl}_tenant ON {tbl}
            FOR ALL TO public
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
    for tbl in _RLS_PLATFORM_EXEMPT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_tenant ON {tbl}")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY")
    for tbl in _RLS_TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_tenant ON {tbl}")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY")