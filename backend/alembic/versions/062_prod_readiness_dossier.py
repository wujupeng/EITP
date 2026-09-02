"""PROD 生产就绪证明书表。

Revision ID: 062
Revises: 061
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "062"
down_revision = "061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prod_readiness_dossier",
        sa.Column("dossier_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("dossier_number", sa.String(64), nullable=False, unique=True),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("tenant_scope", sa.String(64), nullable=False),
        sa.Column("verification_run_ids", sa.dialects.postgresql.JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("nine_questions_answers", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'")),
        sa.Column("evidence_aggregate_hash", sa.String(64), nullable=False),
        sa.Column("verdict", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="DRAFT"),
        sa.Column("signer", sa.String(64)),
        sa.Column("signed_at", sa.DateTime(timezone=True)),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        sa.Column("audit_record_id", sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.execute("""
        CREATE OR REPLACE FUNCTION prod_dossier_no_delete() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'EITP_PROD_DOSSIER_NO_DELETE: dossier cannot be deleted';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("CREATE TRIGGER trg_prod_dossier_no_delete BEFORE DELETE ON prod_readiness_dossier FOR EACH ROW EXECUTE FUNCTION prod_dossier_no_delete()")

    op.execute("ALTER TABLE prod_readiness_dossier ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY rls_prod_dossier_tenant ON prod_readiness_dossier FOR ALL TO public
        USING (
            tenant_scope = current_setting('app.current_tenant_id', true)::text
            OR (tenant_scope = 'ALL' AND current_setting('app.is_platform_admin', true) = 'true')
        )
        WITH CHECK (
            tenant_scope = current_setting('app.current_tenant_id', true)::text
            OR (tenant_scope = 'ALL' AND current_setting('app.is_platform_admin', true) = 'true')
        )
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS rls_prod_dossier_tenant ON prod_readiness_dossier")
    op.execute("ALTER TABLE prod_readiness_dossier DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TRIGGER IF EXISTS trg_prod_dossier_no_delete ON prod_readiness_dossier")
    op.execute("DROP FUNCTION IF EXISTS prod_dossier_no_delete()")
    op.drop_table("prod_readiness_dossier")