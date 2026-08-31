"""IAM user tables

Revision ID: 005
Revises: 004
Create Date: 2026-08-29 00:00:00

EITP-IAM-001-T01-07: IAM 用户相关表结构。
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "iam_user",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("email_encrypted", sa.Text, nullable=True),
        sa.Column("phone_encrypted", sa.Text, nullable=True),
        sa.Column("real_name_encrypted", sa.Text, nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("password_salt", sa.String(255), nullable=False),
        sa.Column("account_status", sa.String(20), nullable=False, server_default="pending_activation"),
        sa.Column("failed_login_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_ip", sa.String(45), nullable=True),
        sa.Column("is_platform_admin", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_tenant_admin", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "username", name="uq_iam_user_tenant_username"),
    )

    op.create_table(
        "iam_password_history",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("password_salt", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "iam_password_policy",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scope_level", sa.String(20), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("min_length", sa.Integer, nullable=False, server_default="12"),
        sa.Column("required_char_categories", sa.Integer, nullable=False, server_default="3"),
        sa.Column("history_count", sa.Integer, nullable=False, server_default="5"),
        sa.Column("expire_days", sa.Integer, nullable=False, server_default="90"),
        sa.Column("expire_grace_days", sa.Integer, nullable=False, server_default="30"),
        sa.Column("max_login_attempts", sa.Integer, nullable=False, server_default="5"),
        sa.Column("lockout_duration_minutes", sa.Integer, nullable=False, server_default="15"),
        sa.Column("ip_ban_threshold", sa.Integer, nullable=False, server_default="20"),
        sa.Column("ip_ban_duration_minutes", sa.Integer, nullable=False, server_default="60"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("scope_level", "tenant_id", name="uq_iam_password_policy_scope"),
    )


def downgrade() -> None:
    op.drop_table("iam_password_policy")
    op.drop_table("iam_password_history")
    op.drop_table("iam_user")