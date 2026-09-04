"""BIZ-OPS 操作审计表。

Revision ID: 085
Revises: 084
Create Date: 2026-09-04
"""

from __future__ import annotations

from alembic import op

revision = "085"
down_revision = "084"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE biz_ops_operation_audits (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id     UUID NOT NULL,
            trace_id      VARCHAR(64) NOT NULL,
            operation_type VARCHAR(30) NOT NULL,
            operator_id   UUID NOT NULL,
            entity_type   VARCHAR(50) NOT NULL,
            entity_id     UUID NOT NULL,
            occurred_at   TIMESTAMPTZ NOT NULL,
            audit_data    VARCHAR(8000) NOT NULL DEFAULT '{}',
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_biz_ops_oa_tenant_op_time ON biz_ops_operation_audits (tenant_id, operation_type, occurred_at)")
    op.execute("CREATE INDEX ix_biz_ops_oa_tenant_entity ON biz_ops_operation_audits (tenant_id, entity_type, entity_id)")
    op.execute("CREATE INDEX ix_biz_ops_oa_trace ON biz_ops_operation_audits (trace_id)")

    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_update()
        RETURNS TRIGGER AS $$ BEGIN
            RAISE EXCEPTION '审计记录不可修改 (append-only)';
        END; $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_audit_no_update
        BEFORE UPDATE OR DELETE ON biz_ops_operation_audits
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_update()
    """)

    op.execute("ALTER TABLE biz_ops_operation_audits ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE biz_ops_operation_audits FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY rls_biz_ops_operation_audits_tenant ON biz_ops_operation_audits FOR ALL TO public
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS rls_biz_ops_operation_audits_tenant ON biz_ops_operation_audits")
    op.execute("ALTER TABLE biz_ops_operation_audits NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE biz_ops_operation_audits DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_no_update ON biz_ops_operation_audits")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_update()")
    op.execute("DROP INDEX IF EXISTS ix_biz_ops_oa_trace")
    op.execute("DROP INDEX IF EXISTS ix_biz_ops_oa_tenant_entity")
    op.execute("DROP INDEX IF EXISTS ix_biz_ops_oa_tenant_op_time")
    op.execute("DROP TABLE IF EXISTS biz_ops_operation_audits CASCADE")