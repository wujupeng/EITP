"""PLT 权限注册（40+ 权限）。

Revision ID: 057
Revises: 056
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op

revision = "057"
down_revision = "056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO iam_permission (id, code, name, module, description)
        VALUES
            (gen_random_uuid(), 'plt:audit:query', '审计查询', 'plt', '平台级 - 跨模块审计查询'),
            (gen_random_uuid(), 'plt:audit:export', '审计导出', 'plt', '平台级 - 导出审计记录（需审批）'),
            (gen_random_uuid(), 'plt:audit:tamper', '篡改检测', 'plt', '平台级 - 触发审计哈希链篡改检测'),
            (gen_random_uuid(), 'plt:audit:retention:manage', '保留策略管理', 'plt', '平台级 - 管理审计保留策略'),
            (gen_random_uuid(), 'plt:audit:archive', '审计归档', 'plt', '平台级 - 手动触发审计归档'),
            (gen_random_uuid(), 'plt:consistency:manage', '一致性管理', 'plt', '平台级 - 管理 Outbox + Saga'),
            (gen_random_uuid(), 'plt:consistency:outbox:retry', 'Outbox重投', 'plt', '平台级 - 重投 Outbox 事件'),
            (gen_random_uuid(), 'plt:consistency:saga:compensate', 'Saga补偿', 'plt', '平台级 - 手动触发 Saga 补偿'),
            (gen_random_uuid(), 'plt:idempotency:manage', '幂等管理', 'plt', '平台级 - 管理幂等记录'),
            (gen_random_uuid(), 'plt:permission:manage', '权限矩阵管理', 'plt', '平台级 - 管理权限矩阵'),
            (gen_random_uuid(), 'plt:permission:approve', '权限审批', 'plt', '平台级 - 审批权限变更'),
            (gen_random_uuid(), 'plt:permission:menu:manage', '菜单管理', 'plt', '平台级 - 管理菜单树'),
            (gen_random_uuid(), 'plt:tenant:manage', '租户管理', 'plt', '平台级 - 管理租户生命周期'),
            (gen_random_uuid(), 'plt:tenant:freeze', '冻结租户', 'plt', '平台级 - 冻结租户'),
            (gen_random_uuid(), 'plt:tenant:archive', '归档租户', 'plt', '平台级 - 归档租户'),
            (gen_random_uuid(), 'plt:tenant:quota:manage', '配额管理', 'plt', '平台级 - 管理租户配额'),
            (gen_random_uuid(), 'plt:config:manage', '配置管理', 'plt', '平台级 - 管理配置中心'),
            (gen_random_uuid(), 'plt:config:decrypt', '配置解密', 'plt', '平台级 - 解密敏感配置项'),
            (gen_random_uuid(), 'plt:config:view', '配置查看', 'plt', '平台级 - 查看配置'),
            (gen_random_uuid(), 'plt:config:gray:manage', '灰度管理', 'plt', '平台级 - 管理配置灰度发布'),
            (gen_random_uuid(), 'plt:job:manage', 'Job管理', 'plt', '平台级 - 管理定时任务'),
            (gen_random_uuid(), 'plt:job:execute', 'Job执行', 'plt', '平台级 - 手动执行 Job'),
            (gen_random_uuid(), 'plt:job:cancel', 'Job取消', 'plt', '平台级 - 取消运行中 Job'),
            (gen_random_uuid(), 'plt:api:manage', 'API治理', 'plt', '平台级 - 管理 API 版本契约'),
            (gen_random_uuid(), 'plt:api:ratelimit:manage', '限流管理', 'plt', '平台级 - 管理限流配置'),
            (gen_random_uuid(), 'plt:observability:view', '可观测性查看', 'plt', '平台级 - 查看 Metrics/Trace/Log'),
            (gen_random_uuid(), 'plt:observability:dashboard', '仪表盘', 'plt', '平台级 - 查看 Grafana 仪表盘'),
            (gen_random_uuid(), 'plt:performance:view', '性能查看', 'plt', '平台级 - 查看性能基线'),
            (gen_random_uuid(), 'plt:performance:baseline:manage', '基线管理', 'plt', '平台级 - 管理性能基线'),
            (gen_random_uuid(), 'plt:cicd:manage', 'CI/CD管理', 'plt', '平台级 - 管理 CI/CD 流水线'),
            (gen_random_uuid(), 'plt:cicd:deploy', '部署', 'plt', '平台级 - 执行部署'),
            (gen_random_uuid(), 'plt:cicd:rollback', '回滚', 'plt', '平台级 - 执行回滚'),
            (gen_random_uuid(), 'plt:dashboard:view', '仪表盘查看', 'plt', '平台级 - 查看平台总览仪表盘'),
            (gen_random_uuid(), 'plt:role:manage', '角色管理', 'plt', '平台级 - 管理 PostgreSQL 角色模型'),
            (gen_random_uuid(), 'plt:errorcode:query', '错误码查询', 'plt', '平台级 - 查询错误码注册表'),
            (gen_random_uuid(), 'plt:health:view', '健康检查', 'plt', '平台级 - 查看健康检查状态'),
            (gen_random_uuid(), 'plt:outbox:query', 'Outbox查询', 'plt', '平台级 - 查询 Outbox 事件'),
            (gen_random_uuid(), 'plt:saga:query', 'Saga查询', 'plt', '平台级 - 查询 Saga 实例'),
            (gen_random_uuid(), 'plt:tenant:init', '租户初始化', 'plt', '平台级 - 初始化新租户'),
            (gen_random_uuid(), 'plt:menu:view', '菜单查看', 'plt', '平台级 - 查看菜单树')
        ON CONFLICT (code) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM iam_permission WHERE module = 'plt'")