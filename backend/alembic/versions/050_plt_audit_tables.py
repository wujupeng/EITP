"""PLT 统一审计中心表 + append-only 触发器。

Revision ID: 050
Revises: 049
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "050"
down_revision = "049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plt_audit_record",
        sa.Column("audit_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("module", sa.String(16), nullable=False),
        sa.Column("aggregate_root_type", sa.String(64), nullable=False),
        sa.Column("aggregate_root_id", sa.String(64), nullable=False),
        sa.Column("operation_type", sa.String(48), nullable=False),
        sa.Column("operator_id", sa.String(64), nullable=False),
        sa.Column("before_snapshot", sa.dialects.postgresql.JSONB),
        sa.Column("after_snapshot", sa.dialects.postgresql.JSONB),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("record_hash", sa.String(64), nullable=False),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("immutable", sa.Boolean, nullable=False, server_default=sa.text("true")),
    )

    op.create_table(
        "plt_audit_retention_policy",
        sa.Column("policy_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("module", sa.String(16), nullable=False),
        sa.Column("retention_days", sa.Integer, nullable=False, server_default="365"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "module", name="uq_plt_audit_retention_tenant_module"),
    )

    op.execute("""
        CREATE OR REPLACE FUNCTION plt_audit_block_modify() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'EITP_PLT_AUDIT_UPDATE_FORBIDDEN: audit records are append-only';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("CREATE TRIGGER plt_audit_no_update BEFORE UPDATE ON plt_audit_record FOR EACH ROW EXECUTE FUNCTION plt_audit_block_modify()")
    op.execute("CREATE TRIGGER plt_audit_no_delete BEFORE DELETE ON plt_audit_record FOR EACH ROW EXECUTE FUNCTION plt_audit_block_modify()")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS plt_audit_no_delete ON plt_audit_record")
    op.execute("DROP TRIGGER IF EXISTS plt_audit_no_update ON plt_audit_record")
    op.execute("DROP FUNCTION IF EXISTS plt_audit_block_modify()")
    op.drop_table("plt_audit_retention_policy")
    op.drop_table("plt_audit_record")