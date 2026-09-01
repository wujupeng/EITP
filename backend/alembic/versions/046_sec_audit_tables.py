"""SEC 审计表 + 平台管理员表 + Redis 违规表 + 证据快照表 + append-only 触发器。

Revision ID: 046
Revises: 045
Create Date: 2026-09-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "046"
down_revision = "045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sec_certification_audit",
        sa.Column("audit_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("batch_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("sec_certification_batch.batch_id"), nullable=False),
        sa.Column("item_id", sa.String(128)),
        sa.Column("action_type", sa.String(32), nullable=False),
        sa.Column("action_time", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("operator", sa.String(64), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("before_value", sa.dialects.postgresql.JSONB),
        sa.Column("after_value", sa.dialects.postgresql.JSONB),
        sa.Column("evidence", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'")),
        sa.Column("immutable", sa.Boolean, server_default=sa.text("true")),
    )

    op.create_table(
        "sec_platform_admin_access_request",
        sa.Column("request_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("applicant", sa.String(64), nullable=False),
        sa.Column("target_tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_data_scope", sa.String(128), nullable=False),
        sa.Column("reason", sa.String(512), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("approval_status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("approver", sa.String(64)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("temp_permission_ttl", sa.Integer, server_default="7200"),
        sa.Column("access_audit_index", sa.String(128)),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
    )

    op.create_table(
        "sec_platform_admin_access_log",
        sa.Column("log_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("request_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("sec_platform_admin_access_request.request_id"), nullable=False),
        sa.Column("access_time", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("accessed_resource", sa.String(256), nullable=False),
        sa.Column("access_result", sa.String(16), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("immutable", sa.Boolean, server_default=sa.text("true")),
    )

    op.create_table(
        "sec_redis_key_violation",
        sa.Column("violation_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("batch_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("sec_certification_batch.batch_id")),
        sa.Column("violation_key", sa.String(256), nullable=False),
        sa.Column("violation_type", sa.String(32), nullable=False),
        sa.Column("expected_prefix", sa.String(128)),
        sa.Column("actual_prefix", sa.String(128)),
        sa.Column("discovered_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("handling_status", sa.String(16), server_default="pending"),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True)),
    )

    op.create_table(
        "sec_evidence_snapshot",
        sa.Column("snapshot_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("item_id", sa.String(128), sa.ForeignKey("sec_certification_item.item_id"), nullable=False),
        sa.Column("request_log", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'")),
        sa.Column("response_log", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'")),
        sa.Column("sql_plan", sa.Text),
        sa.Column("rls_hits", sa.dialects.postgresql.JSONB, server_default=sa.text("'[]'")),
        sa.Column("redis_keys", sa.dialects.postgresql.JSONB, server_default=sa.text("'[]'")),
        sa.Column("audit_records", sa.dialects.postgresql.JSONB, server_default=sa.text("'[]'")),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.execute("""
        CREATE OR REPLACE FUNCTION sec_prevent_audit_tamper() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'EITP_SEC_AUDIT_TAMPER_ATTEMPT: append-only table % cannot be modified', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("CREATE TRIGGER sec_audit_no_update BEFORE UPDATE ON sec_certification_audit FOR EACH ROW EXECUTE FUNCTION sec_prevent_audit_tamper()")
    op.execute("CREATE TRIGGER sec_audit_no_delete BEFORE DELETE ON sec_certification_audit FOR EACH ROW EXECUTE FUNCTION sec_prevent_audit_tamper()")
    op.execute("CREATE TRIGGER sec_access_log_no_update BEFORE UPDATE ON sec_platform_admin_access_log FOR EACH ROW EXECUTE FUNCTION sec_prevent_audit_tamper()")
    op.execute("CREATE TRIGGER sec_access_log_no_delete BEFORE DELETE ON sec_platform_admin_access_log FOR EACH ROW EXECUTE FUNCTION sec_prevent_audit_tamper()")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS sec_access_log_no_delete ON sec_platform_admin_access_log")
    op.execute("DROP TRIGGER IF EXISTS sec_access_log_no_update ON sec_platform_admin_access_log")
    op.execute("DROP TRIGGER IF EXISTS sec_audit_no_delete ON sec_certification_audit")
    op.execute("DROP TRIGGER IF EXISTS sec_audit_no_update ON sec_certification_audit")
    op.execute("DROP FUNCTION IF EXISTS sec_prevent_audit_tamper()")
    op.drop_table("sec_evidence_snapshot")
    op.drop_table("sec_redis_key_violation")
    op.drop_table("sec_platform_admin_access_log")
    op.drop_table("sec_platform_admin_access_request")
    op.drop_table("sec_certification_audit")