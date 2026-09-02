"""REL Core Freeze 冻结声明表 + 状态流转触发器。

Revision ID: 067
Revises: 066
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "067"
down_revision = "066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rel_core_freeze_declaration",
        sa.Column("declaration_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("release_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("rel_release.release_id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("freeze_scope", sa.dialects.postgresql.JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("freeze_time", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("freeze_baseline_hash", sa.String(64), nullable=False),
        sa.Column("unfreeze_process_definition", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'")),
        sa.Column("subsequent_milestone_rules", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'")),
        sa.Column("declaration_status", sa.String(16), nullable=False, server_default="DRAFT"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.execute("""
        CREATE OR REPLACE FUNCTION rel_freeze_declaration_guard() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'EITP_REL_FREEZE_DECLARATION_NO_DELETE: freeze declaration cannot be deleted';
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF OLD.declaration_status = 'EFFECTIVE' THEN
                    RAISE EXCEPTION 'EITP_REL_FREEZE_DECLARATION_EFFECTIVE_LOCKED: EFFECTIVE declaration is immutable';
                END IF;
                IF OLD.declaration_status = 'DRAFT' AND NEW.declaration_status NOT IN ('DRAFT', 'EFFECTIVE') THEN
                    RAISE EXCEPTION 'EITP_REL_FREEZE_DECLARATION_INVALID_TRANSITION: only DRAFT->EFFECTIVE allowed';
                END IF;
                IF OLD.declaration_status = 'REVOKED' THEN
                    RAISE EXCEPTION 'EITP_REL_FREEZE_DECLARATION_REVOKED_LOCKED: REVOKED declaration is immutable';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("CREATE TRIGGER trg_rel_freeze_declaration_guard BEFORE DELETE OR UPDATE ON rel_core_freeze_declaration FOR EACH ROW EXECUTE FUNCTION rel_freeze_declaration_guard()")

    op.execute("ALTER TABLE rel_core_freeze_declaration ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY rls_rel_freeze_declaration_platform_admin ON rel_core_freeze_declaration FOR ALL TO public
        USING (current_setting('app.is_platform_admin', true) = 'true')
        WITH CHECK (current_setting('app.is_platform_admin', true) = 'true')
    """)

    op.create_index("idx_rel_freeze_status", "rel_core_freeze_declaration", ["declaration_status"])
    op.create_index("idx_rel_freeze_hash", "rel_core_freeze_declaration", ["freeze_baseline_hash"])


def downgrade() -> None:
    op.drop_index("idx_rel_freeze_hash", table_name="rel_core_freeze_declaration")
    op.drop_index("idx_rel_freeze_status", table_name="rel_core_freeze_declaration")
    op.execute("DROP POLICY IF EXISTS rls_rel_freeze_declaration_platform_admin ON rel_core_freeze_declaration")
    op.execute("ALTER TABLE rel_core_freeze_declaration DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TRIGGER IF EXISTS trg_rel_freeze_declaration_guard ON rel_core_freeze_declaration")
    op.execute("DROP FUNCTION IF EXISTS rel_freeze_declaration_guard()")
    op.drop_table("rel_core_freeze_declaration")