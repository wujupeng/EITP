"""PLT SEC-001 遗留修复标记。

Revision ID: 059
Revises: 058
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "059"
down_revision = "058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plt_sec_legacy_fix",
        sa.Column("fix_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("fix_name", sa.String(128), nullable=False),
        sa.Column("fix_description", sa.Text, nullable=False),
        sa.Column("fixed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("verified", sa.Boolean, nullable=False, server_default=sa.text("true")),
    )

    op.execute("""
        INSERT INTO plt_sec_legacy_fix (fix_name, fix_description) VALUES
            ('get_items_by_layer_exact_prefix', '修复 get_items_by_layer 子串匹配为精确前缀匹配，避免跨层误匹配'),
            ('aggregate_roots_deepcopy', '修复 aggregate_roots 浅拷贝为 copy.deepcopy，确保每实例独立'),
            ('postgres_role_model', '建立 4 个 PostgreSQL 角色：eitp_app_role/eitp_wms_service_role/eitp_readonly_role/eitp_platform_role')
    """)


def downgrade() -> None:
    op.drop_table("plt_sec_legacy_fix")