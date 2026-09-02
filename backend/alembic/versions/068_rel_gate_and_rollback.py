"""REL 封版门禁记录表 + 回滚方案记录表。

Revision ID: 068
Revises: 067
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "068"
down_revision = "067"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rel_seal_gate_record",
        sa.Column("gate_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("release_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("rel_release.release_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("gate_type", sa.String(32), nullable=False),
        sa.Column("gate_result", sa.String(8), nullable=False),
        sa.Column("gate_detail", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'")),
        sa.Column("gate_time", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("executed_by", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("release_id", "gate_type", name="uq_rel_gate_release_type"),
    )

    op.execute("""
        CREATE OR REPLACE FUNCTION rel_gate_reject_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'EITP_REL_GATE_RECORD_IMMUTABLE: append-only table cannot be modified';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("CREATE TRIGGER trg_rel_gate_immutable BEFORE UPDATE OR DELETE ON rel_seal_gate_record FOR EACH ROW EXECUTE FUNCTION rel_gate_reject_mutation()")

    op.execute("ALTER TABLE rel_seal_gate_record ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY rls_rel_gate_platform_admin ON rel_seal_gate_record FOR ALL TO public
        USING (current_setting('app.is_platform_admin', true) = 'true')
        WITH CHECK (current_setting('app.is_platform_admin', true) = 'true')
    """)

    op.create_index("idx_rel_gate_release", "rel_seal_gate_record", ["release_id"])
    op.create_index("idx_rel_gate_type", "rel_seal_gate_record", ["gate_type"])

    op.create_table(
        "rel_rollback_plan",
        sa.Column("rollback_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("release_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("rel_release.release_id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("version_rollback_sop", sa.dialects.postgresql.JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("database_rollback_migrations", sa.dialects.postgresql.JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("config_rollback_plan", sa.dialects.postgresql.JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("drill_status", sa.String(20), nullable=False, server_default="NOT_DRILLED"),
        sa.Column("drill_result", sa.dialects.postgresql.JSONB),
        sa.Column("plan_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.execute("""
        CREATE OR REPLACE FUNCTION rel_rollback_plan_partial_update() RETURNS trigger AS $$
        BEGIN
            IF NEW.version_rollback_sop IS DISTINCT FROM OLD.version_rollback_sop
               OR NEW.database_rollback_migrations IS DISTINCT FROM OLD.database_rollback_migrations
               OR NEW.config_rollback_plan IS DISTINCT FROM OLD.config_rollback_plan
               OR NEW.plan_hash IS DISTINCT FROM OLD.plan_hash
               OR NEW.release_id IS DISTINCT FROM OLD.release_id THEN
                RAISE EXCEPTION 'EITP_REL_ROLLBACK_PLAN_IMMUTABLE: only drill_status/drill_result/updated_at can be updated';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("CREATE TRIGGER trg_rel_rollback_plan_partial_update BEFORE UPDATE ON rel_rollback_plan FOR EACH ROW EXECUTE FUNCTION rel_rollback_plan_partial_update()")

    op.execute("""
        CREATE OR REPLACE FUNCTION rel_rollback_plan_no_delete() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'EITP_REL_ROLLBACK_PLAN_NO_DELETE: rollback plan cannot be deleted';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("CREATE TRIGGER trg_rel_rollback_plan_no_delete BEFORE DELETE ON rel_rollback_plan FOR EACH ROW EXECUTE FUNCTION rel_rollback_plan_no_delete()")

    op.execute("ALTER TABLE rel_rollback_plan ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY rls_rel_rollback_platform_admin ON rel_rollback_plan FOR ALL TO public
        USING (current_setting('app.is_platform_admin', true) = 'true')
        WITH CHECK (current_setting('app.is_platform_admin', true) = 'true')
    """)

    op.create_index("idx_rel_rollback_release", "rel_rollback_plan", ["release_id"])
    op.create_index("idx_rel_rollback_drill", "rel_rollback_plan", ["drill_status"])


def downgrade() -> None:
    op.drop_index("idx_rel_rollback_drill", table_name="rel_rollback_plan")
    op.drop_index("idx_rel_rollback_release", table_name="rel_rollback_plan")
    op.execute("DROP POLICY IF EXISTS rls_rel_rollback_platform_admin ON rel_rollback_plan")
    op.execute("ALTER TABLE rel_rollback_plan DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TRIGGER IF EXISTS trg_rel_rollback_plan_no_delete ON rel_rollback_plan")
    op.execute("DROP FUNCTION IF EXISTS rel_rollback_plan_no_delete()")
    op.execute("DROP TRIGGER IF EXISTS trg_rel_rollback_plan_partial_update ON rel_rollback_plan")
    op.execute("DROP FUNCTION IF EXISTS rel_rollback_plan_partial_update()")
    op.drop_table("rel_rollback_plan")

    op.drop_index("idx_rel_gate_type", table_name="rel_seal_gate_record")
    op.drop_index("idx_rel_gate_release", table_name="rel_seal_gate_record")
    op.execute("DROP POLICY IF EXISTS rls_rel_gate_platform_admin ON rel_seal_gate_record")
    op.execute("ALTER TABLE rel_seal_gate_record DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TRIGGER IF EXISTS trg_rel_gate_immutable ON rel_seal_gate_record")
    op.execute("DROP FUNCTION IF EXISTS rel_gate_reject_mutation()")
    op.drop_table("rel_seal_gate_record")