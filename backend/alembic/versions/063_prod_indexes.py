"""PROD 复合索引。

Revision ID: 063
Revises: 062
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op

revision = "063"
down_revision = "062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("idx_prod_run_time_tenant_item", "prod_verification_run", ["created_at", "tenant_id", "verification_item"])
    op.create_index("idx_prod_run_item_conclusion", "prod_verification_run", ["verification_item", "conclusion"])
    op.create_index("idx_prod_run_trace_id", "prod_verification_run", ["trace_id"])
    op.create_index("idx_prod_run_executor", "prod_verification_run", ["executor", "created_at"])

    op.create_index("idx_prod_evidence_run_id", "prod_verification_evidence", ["run_id"])
    op.create_index("idx_prod_evidence_trace_id", "prod_verification_evidence", ["trace_id"])

    op.create_index("idx_prod_dossier_status", "prod_readiness_dossier", ["status", "created_at"])
    op.create_index("idx_prod_dossier_verdict", "prod_readiness_dossier", ["verdict", "tenant_scope"])


def downgrade() -> None:
    op.drop_index("idx_prod_dossier_verdict", table_name="prod_readiness_dossier")
    op.drop_index("idx_prod_dossier_status", table_name="prod_readiness_dossier")
    op.drop_index("idx_prod_evidence_trace_id", table_name="prod_verification_evidence")
    op.drop_index("idx_prod_evidence_run_id", table_name="prod_verification_evidence")
    op.drop_index("idx_prod_run_executor", table_name="prod_verification_run")
    op.drop_index("idx_prod_run_trace_id", table_name="prod_verification_run")
    op.drop_index("idx_prod_run_item_conclusion", table_name="prod_verification_run")
    op.drop_index("idx_prod_run_time_tenant_item", table_name="prod_verification_run")