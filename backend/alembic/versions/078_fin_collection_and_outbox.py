"""FIN 催收任务表 + 催收记录表（append-only）+ 领域事件出库表。

Revision ID: 078
Revises: 077
Create Date: 2026-09-03
"""

from __future__ import annotations

from alembic import op

revision = "078"
down_revision = "077"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE fin_collection_task (
            task_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           UUID NOT NULL,
            ar_voucher_no       VARCHAR(64) NOT NULL,
            overdue_amount      NUMERIC(18,2) NOT NULL DEFAULT 0,
            overdue_days        INTEGER NOT NULL DEFAULT 0,
            collection_stage    VARCHAR(32) NOT NULL DEFAULT 'REMINDER',
            status              VARCHAR(32) NOT NULL DEFAULT 'PENDING',
            assigned_to         VARCHAR(64),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_fin_collection_task UNIQUE (tenant_id, ar_voucher_no, collection_stage)
        )
    """)
    op.execute("CREATE INDEX idx_fin_collection_task_tenant_status ON fin_collection_task (tenant_id, status)")
    op.execute("CREATE INDEX idx_fin_collection_task_ar ON fin_collection_task (tenant_id, ar_voucher_no)")

    op.execute("""
        CREATE TABLE fin_collection_record (
            record_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           UUID NOT NULL,
            task_id             UUID NOT NULL REFERENCES fin_collection_task(task_id),
            collection_result   VARCHAR(64) NOT NULL,
            record_text         TEXT,
            handled_by          VARCHAR(64) NOT NULL,
            handled_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_fin_collection_record_task ON fin_collection_record (tenant_id, task_id)")

    op.execute("""
        CREATE OR REPLACE FUNCTION fin_reject_collection_record_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'EITP_FIN_COLLECTION_RECORD_IMMUTABLE: append-only table cannot be modified';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_fin_collection_record_immutable
        BEFORE UPDATE OR DELETE ON fin_collection_record
        FOR EACH ROW EXECUTE FUNCTION fin_reject_collection_record_mutation()
    """)

    op.execute("""
        CREATE TABLE fin_event_outbox (
            event_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           UUID NOT NULL,
            event_type          VARCHAR(128) NOT NULL,
            event_payload       JSONB NOT NULL DEFAULT '{}'::jsonb,
            aggregate_id        VARCHAR(128) NOT NULL,
            trace_id            VARCHAR(128),
            published           BOOLEAN NOT NULL DEFAULT FALSE,
            publish_attempts    INTEGER NOT NULL DEFAULT 0,
            last_publish_at     TIMESTAMPTZ,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_fin_event_outbox_unpublished ON fin_event_outbox (publish_attempts) WHERE published = FALSE")
    op.execute("CREATE INDEX idx_fin_event_outbox_tenant_type ON fin_event_outbox (tenant_id, event_type)")
    op.execute("CREATE INDEX idx_fin_event_outbox_aggregate ON fin_event_outbox (aggregate_id)")

    for tbl in ["fin_collection_task", "fin_collection_record", "fin_event_outbox"]:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY rls_{tbl}_tenant ON {tbl} FOR ALL TO public
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """)
        op.execute(f"""
            CREATE POLICY rls_{tbl}_platform_admin ON {tbl} FOR ALL TO public
            USING (current_setting('app.is_platform_admin', true) = 'true')
            WITH CHECK (current_setting('app.is_platform_admin', true) = 'true')
        """)


def downgrade() -> None:
    for tbl in ["fin_event_outbox", "fin_collection_record", "fin_collection_task"]:
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_platform_admin ON {tbl}")
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_tenant ON {tbl}")
        op.execute(f"ALTER TABLE {tbl} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY")

    op.execute("DROP INDEX IF EXISTS idx_fin_event_outbox_aggregate")
    op.execute("DROP INDEX IF EXISTS idx_fin_event_outbox_tenant_type")
    op.execute("DROP INDEX IF EXISTS idx_fin_event_outbox_unpublished")
    op.execute("DROP TABLE IF EXISTS fin_event_outbox CASCADE")

    op.execute("DROP TRIGGER IF EXISTS trg_fin_collection_record_immutable ON fin_collection_record")
    op.execute("DROP FUNCTION IF EXISTS fin_reject_collection_record_mutation()")
    op.execute("DROP INDEX IF EXISTS idx_fin_collection_record_task")
    op.execute("DROP TABLE IF EXISTS fin_collection_record CASCADE")

    op.execute("DROP INDEX IF EXISTS idx_fin_collection_task_ar")
    op.execute("DROP INDEX IF EXISTS idx_fin_collection_task_tenant_status")
    op.execute("DROP TABLE IF EXISTS fin_collection_task CASCADE")