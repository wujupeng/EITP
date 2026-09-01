"""SEC 权限注册 + 菜单子树注入。

Revision ID: 048
Revises: 047
Create Date: 2026-09-01
"""

from __future__ import annotations

from alembic import op

revision = "048"
down_revision = "047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO iam_permission (id, code, name, module, description)
        VALUES
            (gen_random_uuid(), 'sec:cert:execute', '执行认证', 'sec', '平台级 - 执行多租户隔离认证矩阵'),
            (gen_random_uuid(), 'sec:cert:issue', '颁发证书', 'sec', '平台级 - 颁发认证证书'),
            (gen_random_uuid(), 'sec:cert:revoke', '撤销证书', 'sec', '平台级 - 撤销认证证书'),
            (gen_random_uuid(), 'sec:cert:verify', '验证证书', 'sec', '平台级 - 验证证书签名与有效性'),
            (gen_random_uuid(), 'sec:report:view', '查看报告', 'sec', '平台级 - 查看认证报告'),
            (gen_random_uuid(), 'sec:report:export', '导出报告', 'sec', '平台级 - 导出认证报告'),
            (gen_random_uuid(), 'sec:report:evidence:view', '查看证据', 'sec', '平台级 - 查看认证证据快照'),
            (gen_random_uuid(), 'sec:config:manage', '配置管理', 'sec', '平台级 - 管理认证配置'),
            (gen_random_uuid(), 'sec:config:item:skip', '跳过认证项', 'sec', '平台级 - 跳过特定认证项（需原因）'),
            (gen_random_uuid(), 'sec:audit:view', '查看审计', 'sec', '平台级 - 查看认证审计日志'),
            (gen_random_uuid(), 'sec:audit:export', '导出审计', 'sec', '平台级 - 导出认证审计日志'),
            (gen_random_uuid(), 'sec:platform:access:request', '申请访问', 'sec', '平台级 - 申请访问企业业务数据'),
            (gen_random_uuid(), 'sec:platform:access:approve', '审批访问', 'sec', '平台级 - 审批平台管理员访问申请'),
            (gen_random_uuid(), 'sec:redis:scan', 'Redis扫描', 'sec', '平台级 - 扫描Redis Key前缀合规性'),
            (gen_random_uuid(), 'sec:join:test', 'JOIN测试', 'sec', '平台级 - 执行JOIN跨租户泄露测试'),
            (gen_random_uuid(), 'sec:attack:chain', '攻击链', 'sec', '平台级 - 执行14步E2E攻击链验证')
        ON CONFLICT (code) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM iam_permission WHERE module = 'sec'")