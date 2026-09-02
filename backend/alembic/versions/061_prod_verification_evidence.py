"""PROD 验证证据索引表 + append-only 触发器。

Revision ID: 061
Revises: 060
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "061"
down_revision = "060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prod_verification_evidence",
        sa.Column("evidence_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("prod_verification_run.run_id"), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_type", sa.String(20), nullable=False),
        sa.Column("storage_path", sa.String(512), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger, nullable=False),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.execute("CREATE TRIGGER trg_prod_evidence_immutable BEFORE UPDATE OR DELETE ON prod_verification_evidence FOR EACH ROW EXECUTE FUNCTION prod_reject_mutation()")

    op.execute("ALTER TABLE prod_verification_evidence ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY rls_prod_evidence_tenant ON prod_verification_evidence FOR ALL TO public
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
    op.execute("DROP POLICY IF EXISTS rls_prod_evidence_tenant ON prod_verification_evidence")
    op.execute("ALTER TABLE prod_verification_evidence DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TRIGGER IF EXISTS trg_prod_evidence_immutable ON prod_verification_evidence")
    op.drop_table("prod_verification_evidence")