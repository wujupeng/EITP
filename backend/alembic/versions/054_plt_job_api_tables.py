"""PLT Job + API 表。

Revision ID: 054
Revises: 053
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "054"
down_revision = "053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plt_job_definition",
        sa.Column("job_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_name", sa.String(128), nullable=False, unique=True),
        sa.Column("cron_expression", sa.String(64), nullable=False),
        sa.Column("handler_ref", sa.String(256), nullable=False),
        sa.Column("timeout_seconds", sa.Integer, nullable=False),
        sa.Column("retry_policy", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column("concurrency_strategy", sa.String(16), nullable=False),
        sa.Column("tenant_scope", sa.String(16), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True)),
    )

    op.create_table(
        "plt_job_execution",
        sa.Column("execution_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.Integer),
        sa.Column("error_message", sa.Text),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True)),
    )

    op.create_table(
        "plt_api_version_contract",
        sa.Column("contract_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("api_path", sa.String(256), nullable=False),
        sa.Column("version", sa.String(8), nullable=False),
        sa.Column("change_type", sa.String(16), nullable=False),
        sa.Column("introduced_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deprecated_at", sa.DateTime(timezone=True)),
        sa.Column("sunset_at", sa.DateTime(timezone=True)),
        sa.Column("migration_guide", sa.Text),
    )

    op.create_table(
        "plt_rate_limit_config",
        sa.Column("config_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.Column("api_path", sa.String(256), nullable=False),
        sa.Column("qps_limit", sa.Integer, nullable=False),
        sa.Column("burst_size", sa.Integer, nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_table("plt_rate_limit_config")
    op.drop_table("plt_api_version_contract")
    op.drop_table("plt_job_execution")
    op.drop_table("plt_job_definition")