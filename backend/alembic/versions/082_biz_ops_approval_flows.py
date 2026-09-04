"""BIZ-OPS 审批流表。

Revision ID: 082
Revises: 081
Create Date: 2026-09-03
"""

from __future__ import annotations

from alembic import op

revision = "082"
down_revision = "081"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE biz_ops_approval_flows (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id   UUID NOT NULL,
            flow_key    VARCHAR(100) NOT NULL,
            flow_name   VARCHAR(200) NOT NULL,
            entity_type VARCHAR(50) NOT NULL,
            is_active   VARCHAR(5) NOT NULL DEFAULT 'true',
            version     INTEGER NOT NULL DEFAULT 1,
            description VARCHAR(500),
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_biz_ops_af_tenant_flow UNIQUE (tenant_id, flow_key)
        )
    """)
    op.execute("CREATE INDEX ix_biz_ops_af_tenant_entity ON biz_ops_approval_flows (tenant_id, entity_type)")

    op.execute("""
        CREATE TABLE biz_ops_approval_nodes (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           UUID NOT NULL,
            flow_id             UUID NOT NULL,
            node_order          INTEGER NOT NULL,
            node_name           VARCHAR(200) NOT NULL,
            routing_strategy    VARCHAR(20) NOT NULL,
            routing_config      VARCHAR(2000) NOT NULL DEFAULT '{}',
            timeout_seconds     INTEGER NOT NULL DEFAULT 86400,
            timeout_strategy    VARCHAR(20) NOT NULL DEFAULT 'warn_only',
            is_countersign      VARCHAR(5) NOT NULL DEFAULT 'false',
            countersign_ratio   DOUBLE PRECISION NOT NULL DEFAULT 1.0,
            condition_expression VARCHAR(1000),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_biz_ops_an_flow_order ON biz_ops_approval_nodes (flow_id, node_order)")

    op.execute("""
        CREATE TABLE biz_ops_approval_records (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id   UUID NOT NULL,
            approval_id UUID NOT NULL,
            flow_id     UUID NOT NULL,
            node_order  INTEGER NOT NULL,
            action      VARCHAR(20) NOT NULL,
            operator_id UUID NOT NULL,
            comment     VARCHAR(1000),
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_biz_ops_ar_approval ON biz_ops_approval_records (approval_id, node_order)")
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_approval_record_update()
        RETURNS TRIGGER AS $$ BEGIN
            RAISE EXCEPTION '审批记录不可修改 (append-only)';
        END; $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_approval_record_no_update
        BEFORE UPDATE OR DELETE ON biz_ops_approval_records
        FOR EACH ROW EXECUTE FUNCTION prevent_approval_record_update()
    """)

    for table in ["biz_ops_approval_flows", "biz_ops_approval_nodes", "biz_ops_approval_records"]:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY rls_{table}_tenant ON {table} FOR ALL TO public
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """)


def downgrade() -> None:
    for table in ["biz_ops_approval_records", "biz_ops_approval_nodes", "biz_ops_approval_flows"]:
        op.execute(f"DROP POLICY IF EXISTS rls_{table}_tenant ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TRIGGER IF EXISTS trg_approval_record_no_update ON biz_ops_approval_records")
    op.execute("DROP FUNCTION IF EXISTS prevent_approval_record_update()")
    op.execute("DROP INDEX IF EXISTS ix_biz_ops_ar_approval")
    op.execute("DROP TABLE IF EXISTS biz_ops_approval_records CASCADE")
    op.execute("DROP INDEX IF EXISTS ix_biz_ops_an_flow_order")
    op.execute("DROP TABLE IF EXISTS biz_ops_approval_nodes CASCADE")
    op.execute("DROP INDEX IF EXISTS ix_biz_ops_af_tenant_entity")
    op.execute("DROP TABLE IF EXISTS biz_ops_approval_flows CASCADE")