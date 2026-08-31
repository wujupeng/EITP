"""IAM authn tables

Revision ID: 007
Revises: 006
Create Date: 2026-08-29 00:00:02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "iam_refresh_token",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_revoked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "iam_token_revocation",
        sa.Column("jti", sa.String(255), primary_key=True),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("reason", sa.String(100), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "iam_data_scope",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("role_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("iam_role.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("scope_type", sa.String(50), nullable=False),
        sa.Column("access_mode", sa.String(20), nullable=False, server_default="read"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "iam_data_scope_org",
        sa.Column("scope_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("iam_data_scope.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("org_node_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
    )

    op.create_table(
        "iam_data_scope_warehouse",
        sa.Column("scope_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("iam_data_scope.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("warehouse_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("iam_data_scope_warehouse")
    op.drop_table("iam_data_scope_org")
    op.drop_table("iam_data_scope")
    op.drop_table("iam_token_revocation")
    op.drop_table("iam_refresh_token")