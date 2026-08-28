"""initial platform schema

Revision ID: 001
Revises:
Create Date: 2026-08-27 00:00:00

EITP-MT-001-T01-09: 初始迁移 - 创建平台级基础表结构。
支持空库初始化与向前兼容变更。
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_meta",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key", sa.String(255), nullable=False, unique=True),
        sa.Column("value", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "tenant",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("enterprise_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="provisioning"),
        sa.Column("data_placement", sa.String(50), nullable=False, server_default="shared_db"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("idempotency_key", sa.String(255), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_tenant_status", "tenant", ["status"])
    op.create_index("idx_tenant_idempotency", "tenant", ["idempotency_key"])


def downgrade() -> None:
    op.drop_index("idx_tenant_idempotency", table_name="tenant")
    op.drop_index("idx_tenant_status", table_name="tenant")
    op.drop_table("tenant")
    op.drop_table("platform_meta")