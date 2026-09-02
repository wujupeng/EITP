"""PLT 权限 + 租户表。

Revision ID: 053
Revises: 052
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "053"
down_revision = "052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plt_permission_matrix",
        sa.Column("entry_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("role_id", sa.String(64), nullable=False),
        sa.Column("operation", sa.String(128), nullable=False),
        sa.Column("resource_scope", sa.String(32), nullable=False),
        sa.Column("data_scope", sa.String(32), nullable=False),
        sa.Column("decision", sa.String(8), nullable=False),
        sa.Column("approval_status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("approved_by", sa.String(64)),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
    )

    op.create_table(
        "plt_menu_tree",
        sa.Column("menu_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("parent_id", sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.Column("menu_name", sa.String(64), nullable=False),
        sa.Column("menu_path", sa.String(128)),
        sa.Column("permission_code", sa.String(128)),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("visible", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
    )

    op.create_table(
        "plt_permission_approval",
        sa.Column("approval_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("entry_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("applicant", sa.String(64), nullable=False),
        sa.Column("approver", sa.String(64)),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
    )

    op.create_table(
        "plt_tenant_quota",
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("max_users", sa.Integer, nullable=False),
        sa.Column("max_orders_per_day", sa.Integer, nullable=False),
        sa.Column("max_storage_mb", sa.Integer, nullable=False),
        sa.Column("max_api_calls_per_minute", sa.Integer, nullable=False),
        sa.Column("max_concurrent_requests", sa.Integer, nullable=False),
        sa.Column("current_usage", sa.dialects.postgresql.JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "plt_tenant_lifecycle_log",
        sa.Column("log_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_status", sa.String(16), nullable=False),
        sa.Column("to_status", sa.String(16), nullable=False),
        sa.Column("operator", sa.String(64), nullable=False),
        sa.Column("reason", sa.Text),
        sa.Column("transition_time", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("plt_tenant_lifecycle_log")
    op.drop_table("plt_tenant_quota")
    op.drop_table("plt_permission_approval")
    op.drop_table("plt_menu_tree")
    op.drop_table("plt_permission_matrix")