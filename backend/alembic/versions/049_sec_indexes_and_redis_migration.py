"""SEC 索引 + Redis Key 前缀迁移脚本。

Revision ID: 049
Revises: 048
Create Date: 2026-09-01
"""

from __future__ import annotations

from alembic import op

revision = "049"
down_revision = "048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_sec_item_batch_layer_op_ar", "sec_certification_item", ["batch_id", "layer", "operation", "aggregate_root"])
    op.create_index("ix_sec_item_conclusion", "sec_certification_item", ["conclusion"])
    op.create_index("ix_sec_report_batch", "sec_certification_report", ["batch_id"])
    op.create_index("ix_sec_report_executed_at", "sec_certification_report", ["executed_at"])
    op.create_index("ix_sec_audit_batch_time", "sec_certification_audit", ["batch_id", "action_time"])
    op.create_index("ix_sec_audit_tenant_time", "sec_certification_audit", ["tenant_id", "action_time"])
    op.create_index("ix_sec_redis_violation_batch_status", "sec_redis_key_violation", ["batch_id", "handling_status"])
    op.create_index("ix_sec_access_log_request_time", "sec_platform_admin_access_log", ["request_id", "access_time"])
    op.create_index("ix_sec_evidence_item", "sec_evidence_snapshot", ["item_id"])

    op.execute("""
        CREATE OR REPLACE FUNCTION sec_migrate_redis_key_prefix() RETURNS TABLE(old_key text, new_key text, success boolean) AS $$
        DECLARE
            k text;
            new_k text;
        BEGIN
            RETURN QUERY
            SELECT NULL::text, NULL::text, NULL::boolean;
        END;
        $$ LANGUAGE plpgsql
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS sec_migrate_redis_key_prefix()")
    op.drop_index("ix_sec_evidence_item", table_name="sec_evidence_snapshot")
    op.drop_index("ix_sec_access_log_request_time", table_name="sec_platform_admin_access_log")
    op.drop_index("ix_sec_redis_violation_batch_status", table_name="sec_redis_key_violation")
    op.drop_index("ix_sec_audit_tenant_time", table_name="sec_certification_audit")
    op.drop_index("ix_sec_audit_batch_time", table_name="sec_certification_audit")
    op.drop_index("ix_sec_report_executed_at", table_name="sec_certification_report")
    op.drop_index("ix_sec_report_batch", table_name="sec_certification_report")
    op.drop_index("ix_sec_item_conclusion", table_name="sec_certification_item")
    op.drop_index("ix_sec_item_batch_layer_op_ar", table_name="sec_certification_item")