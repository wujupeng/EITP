"""PROD 验证执行记录表 + append-only 触发器。

Revision ID: 060
Revises: 059
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "060"
down_revision = "059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prod_verification_run",
        sa.Column("run_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("verification_item", sa.String(32), nullable=False),
        sa.Column("executor", sa.String(16), nullable=False),
        sa.Column("environment", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("config_snapshot", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'")),
        sa.Column("conclusion", sa.String(16)),
        sa.Column("evidence_report_path", sa.String(512)),
        sa.Column("evidence_metrics_snapshot_path", sa.String(512)),
        sa.Column("evidence_log_path", sa.String(512)),
        sa.Column("evidence_hash", sa.String(64)),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("failure_detail", sa.dialects.postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.execute("""
        CREATE OR REPLACE FUNCTION prod_reject_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'EITP_PROD_VERIFICATION_RECORD_IMMUTABLE: append-only table cannot be modified';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("CREATE TRIGGER trg_prod_run_immutable BEFORE UPDATE OR DELETE ON prod_verification_run FOR EACH ROW EXECUTE FUNCTION prod_reject_mutation()")

    op.execute("ALTER TABLE prod_verification_run ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY rls_prod_run_tenant ON prod_verification_run FOR ALL TO public
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
    op.execute("DROP POLICY IF EXISTS rls_prod_run_tenant ON prod_verification_run")
    op.execute("ALTER TABLE prod_verification_run DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TRIGGER IF EXISTS trg_prod_run_immutable ON prod_verification_run")
    op.execute("DROP FUNCTION IF EXISTS prod_reject_mutation()")
    op.drop_table("prod_verification_run")