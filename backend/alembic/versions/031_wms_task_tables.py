"""WMS Task 与 Task Line 表 - 作业执行载体与状态机。

Revision ID: 031
Revises: 030
Create Date: 2026-08-31
"""

from __future__ import annotations

from alembic import op

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE wms_task ("
        "    task_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id             UUID NOT NULL,"
        "    task_type             VARCHAR(16) NOT NULL,"
        "    document_id           UUID NOT NULL,"
        "    document_type         VARCHAR(32) NOT NULL,"
        "    assignee_id           UUID,"
        "    status                VARCHAR(16) NOT NULL DEFAULT 'created',"
        "    priority              VARCHAR(8) NOT NULL DEFAULT 'medium',"
        "    inv_transaction_ids   JSONB NOT NULL DEFAULT '[]'::jsonb,"
        "    idempotency_key       VARCHAR(128),"
        "    correlation_id        VARCHAR(128),"
        "    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    assigned_at           TIMESTAMPTZ,"
        "    started_at            TIMESTAMPTZ,"
        "    completed_at          TIMESTAMPTZ,"
        "    CONSTRAINT chk_wms_task_type CHECK (task_type IN ('receiving','putaway','picking','transfer','shipping','packing','cycle_count','qc')),"
        "    CONSTRAINT chk_wms_task_status CHECK (status IN ('created','assigned','in_progress','completed','cancelled','failed')),"
        "    CONSTRAINT chk_wms_task_priority CHECK (priority IN ('high','medium','low'))"
        ")"
    )
    op.execute("CREATE INDEX idx_wms_task_status ON wms_task (tenant_id, status)")
    op.execute("CREATE INDEX idx_wms_task_assignee ON wms_task (tenant_id, assignee_id, status)")
    op.execute("CREATE INDEX idx_wms_task_document ON wms_task (tenant_id, document_id)")
    op.execute("CREATE UNIQUE INDEX idx_wms_task_idempotency ON wms_task (tenant_id, idempotency_key) WHERE idempotency_key IS NOT NULL")

    op.execute(
        "CREATE TABLE wms_task_line ("
        "    line_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id             UUID NOT NULL,"
        "    task_id               UUID NOT NULL REFERENCES wms_task(task_id),"
        "    line_no               INT NOT NULL,"
        "    sku_id                UUID NOT NULL,"
        "    location_id           UUID REFERENCES wms_location(location_id),"
        "    target_location_id    UUID REFERENCES wms_location(location_id),"
        "    required_qty          NUMERIC(18,6) NOT NULL CHECK (required_qty >= 0),"
        "    executed_qty          NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (executed_qty >= 0),"
        "    status                VARCHAR(16) NOT NULL DEFAULT 'pending',"
        "    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT uk_wms_task_line_no UNIQUE (task_id, line_no),"
        "    CONSTRAINT chk_wms_task_line_status CHECK (status IN ('pending','in_progress','completed','cancelled','failed'))"
        ")"
    )
    op.execute("CREATE INDEX idx_wms_task_line_task ON wms_task_line (tenant_id, task_id)")
    op.execute("CREATE INDEX idx_wms_task_line_sku ON wms_task_line (tenant_id, sku_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS wms_task_line CASCADE")
    op.execute("DROP TABLE IF EXISTS wms_task CASCADE")