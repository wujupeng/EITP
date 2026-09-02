"""REL 资产快照记录表 + append-only 触发器。

Revision ID: 066
Revises: 065
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "066"
down_revision = "065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rel_asset_snapshot",
        sa.Column("snapshot_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("release_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("rel_release.release_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("asset_type", sa.String(32), nullable=False),
        sa.Column("asset_name", sa.String(256), nullable=False),
        sa.Column("asset_content_hash", sa.String(64), nullable=False),
        sa.Column("archive_location", sa.String(512), nullable=False),
        sa.Column("archive_time", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("archive_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("collected_by", sa.String(64), nullable=False),
        sa.Column("verification_status", sa.String(16), nullable=False, server_default="VERIFIED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("release_id", "asset_type", name="uq_rel_asset_release_type"),
    )

    op.execute("""
        CREATE OR REPLACE FUNCTION rel_asset_reject_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'EITP_REL_ASSET_SNAPSHOT_IMMUTABLE: append-only table cannot be modified';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("CREATE TRIGGER trg_rel_asset_snapshot_immutable BEFORE UPDATE OR DELETE ON rel_asset_snapshot FOR EACH ROW EXECUTE FUNCTION rel_asset_reject_mutation()")

    op.execute("ALTER TABLE rel_asset_snapshot ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY rls_rel_asset_snapshot_platform_admin ON rel_asset_snapshot FOR ALL TO public
        USING (current_setting('app.is_platform_admin', true) = 'true')
        WITH CHECK (current_setting('app.is_platform_admin', true) = 'true')
    """)

    op.create_index("idx_rel_asset_release", "rel_asset_snapshot", ["release_id"])
    op.create_index("idx_rel_asset_type", "rel_asset_snapshot", ["asset_type"])
    op.create_index("idx_rel_asset_hash", "rel_asset_snapshot", ["asset_content_hash"])


def downgrade() -> None:
    op.drop_index("idx_rel_asset_hash", table_name="rel_asset_snapshot")
    op.drop_index("idx_rel_asset_type", table_name="rel_asset_snapshot")
    op.drop_index("idx_rel_asset_release", table_name="rel_asset_snapshot")
    op.execute("DROP POLICY IF EXISTS rls_rel_asset_snapshot_platform_admin ON rel_asset_snapshot")
    op.execute("ALTER TABLE rel_asset_snapshot DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TRIGGER IF EXISTS trg_rel_asset_snapshot_immutable ON rel_asset_snapshot")
    op.execute("DROP FUNCTION IF EXISTS rel_asset_reject_mutation()")
    op.drop_table("rel_asset_snapshot")