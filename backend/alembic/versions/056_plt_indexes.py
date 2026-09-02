"""PLT 复合索引。

Revision ID: 056
Revises: 055
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op

revision = "056"
down_revision = "055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("idx_plt_audit_time_tenant_module", "plt_audit_record", ["timestamp", "tenant_id", "module"], postgresql_using="btree")
    op.create_index("idx_plt_audit_trace_id", "plt_audit_record", ["trace_id"])
    op.create_index("idx_plt_audit_tenant_agg", "plt_audit_record", ["tenant_id", "aggregate_root_type", "aggregate_root_id"])
    op.create_index("idx_plt_audit_operator", "plt_audit_record", ["tenant_id", "operator_id", "timestamp"])

    op.execute("CREATE INDEX idx_plt_outbox_pending ON plt_outbox_event (delivery_status, created_at) WHERE delivery_status = 'PENDING'")
    op.execute("CREATE INDEX idx_plt_outbox_dead_letter ON plt_outbox_event (delivery_status, delivery_attempts) WHERE delivery_status = 'DEAD_LETTER'")

    op.create_index("idx_plt_saga_status", "plt_saga_instance", ["status", "updated_at"])
    op.create_index("idx_plt_saga_tenant", "plt_saga_instance", ["tenant_id", "status"])

    op.create_index("idx_plt_idem_tenant_expires", "plt_idempotency_record", ["tenant_id", "expires_at"])

    op.create_index("idx_plt_config_key_version", "plt_config_revision", ["namespace", "namespace_id", "config_key", "version"])

    op.create_index("idx_plt_job_exec_job_status", "plt_job_execution", ["job_id", "status", "started_at"])


def downgrade() -> None:
    op.drop_index("idx_plt_job_exec_job_status", table_name="plt_job_execution")
    op.drop_index("idx_plt_config_key_version", table_name="plt_config_revision")
    op.drop_index("idx_plt_idem_tenant_expires", table_name="plt_idempotency_record")
    op.drop_index("idx_plt_saga_tenant", table_name="plt_saga_instance")
    op.drop_index("idx_plt_saga_status", table_name="plt_saga_instance")
    op.execute("DROP INDEX IF EXISTS idx_plt_outbox_dead_letter")
    op.execute("DROP INDEX IF EXISTS idx_plt_outbox_pending")
    op.drop_index("idx_plt_audit_operator", table_name="plt_audit_record")
    op.drop_index("idx_plt_audit_tenant_agg", table_name="plt_audit_record")
    op.drop_index("idx_plt_audit_trace_id", table_name="plt_audit_record")
    op.drop_index("idx_plt_audit_time_tenant_module", table_name="plt_audit_record")