"""master data tables

Revision ID: 004
Revises: 003
Create Date: 2026-08-28 00:02:00

EITP-MT-001-T08-01: 创建主数据基准表、公司级覆盖表、仓库级覆盖表。
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "master_data_base",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("enterprise_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku_code", sa.String(255), nullable=False),
        sa.Column("base_attrs", sa.dialects.postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_master_base_enterprise", "master_data_base", ["enterprise_id"])
    op.create_index("idx_master_base_unique", "master_data_base", ["enterprise_id", "sku_code"], unique=True)

    op.create_table(
        "master_data_company_override",
        sa.Column("override_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("master_data_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("master_data_base.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_attrs", sa.dialects.postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_company_override_unique", "master_data_company_override",
                    ["master_data_id", "organization_id"], unique=True)

    op.create_table(
        "master_data_warehouse_override",
        sa.Column("override_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("master_data_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("master_data_base.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_attrs", sa.dialects.postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_warehouse_override_unique", "master_data_warehouse_override",
                    ["master_data_id", "warehouse_id"], unique=True)


def downgrade() -> None:
    op.drop_index("idx_warehouse_override_unique", table_name="master_data_warehouse_override")
    op.drop_table("master_data_warehouse_override")
    op.drop_index("idx_company_override_unique", table_name="master_data_company_override")
    op.drop_table("master_data_company_override")
    op.drop_index("idx_master_base_unique", table_name="master_data_base")
    op.drop_index("idx_master_base_enterprise", table_name="master_data_base")
    op.drop_table("master_data_base")