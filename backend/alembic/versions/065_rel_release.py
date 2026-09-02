"""REL 封版记录表 + append-only 触发器。

Revision ID: 065
Revises: 064
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "065"
down_revision = "064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rel_release",
        sa.Column("release_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("release_number", sa.String(64), nullable=False, unique=True),
        sa.Column("version", sa.String(32), nullable=False, unique=True),
        sa.Column("git_tag", sa.String(128), nullable=False, unique=True),
        sa.Column("git_commit_sha", sa.String(64), nullable=False),
        sa.Column("seal_time", sa.DateTime(timezone=True)),
        sa.Column("seal_status", sa.String(24), nullable=False, server_default="REQUESTED"),
        sa.Column("verdict", sa.String(16)),
        sa.Column("signed_by_releaser", sa.String(64)),
        sa.Column("signed_by_security", sa.String(64)),
        sa.Column("signed_at", sa.DateTime(timezone=True)),
        sa.Column("core_freeze_baseline_hash", sa.String(64)),
        sa.Column("test_total_count", sa.Integer),
        sa.Column("test_passed_count", sa.Integer),
        sa.Column("evidence_hash", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.execute("""
        CREATE OR REPLACE FUNCTION rel_reject_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'EITP_REL_RELEASE_IMMUTABLE: append-only table cannot be modified';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("CREATE TRIGGER trg_rel_release_immutable BEFORE UPDATE OR DELETE ON rel_release FOR EACH ROW EXECUTE FUNCTION rel_reject_mutation()")

    op.execute("ALTER TABLE rel_release ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY rls_rel_release_platform_admin ON rel_release FOR ALL TO public
        USING (current_setting('app.is_platform_admin', true) = 'true')
        WITH CHECK (current_setting('app.is_platform_admin', true) = 'true')
    """)

    op.create_index("idx_rel_release_status", "rel_release", ["seal_status"])
    op.create_index("idx_rel_release_verdict", "rel_release", ["verdict"])


def downgrade() -> None:
    op.drop_index("idx_rel_release_verdict", table_name="rel_release")
    op.drop_index("idx_rel_release_status", table_name="rel_release")
    op.execute("DROP POLICY IF EXISTS rls_rel_release_platform_admin ON rel_release")
    op.execute("ALTER TABLE rel_release DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TRIGGER IF EXISTS trg_rel_release_immutable ON rel_release")
    op.execute("DROP FUNCTION IF EXISTS rel_reject_mutation()")
    op.drop_table("rel_release")