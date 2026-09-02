"""PLT 幂等 + 配置表。

Revision ID: 052
Revises: 051
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "052"
down_revision = "051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plt_idempotency_record",
        sa.Column("idempotency_key", sa.String(256), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("response_cache", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column("response_status", sa.Integer, nullable=False),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "plt_config_revision",
        sa.Column("revision_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("namespace", sa.String(16), nullable=False),
        sa.Column("namespace_id", sa.String(64)),
        sa.Column("config_key", sa.String(128), nullable=False),
        sa.Column("config_value", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column("value_type", sa.String(16), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("value_range", sa.dialects.postgresql.JSONB),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("changed_by", sa.String(64), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("gray_release_config", sa.dialects.postgresql.JSONB),
        sa.UniqueConstraint("namespace", "namespace_id", "config_key", "version", name="uq_plt_config_namespace_key_version"),
    )


def downgrade() -> None:
    op.drop_table("plt_config_revision")
    op.drop_table("plt_idempotency_record")