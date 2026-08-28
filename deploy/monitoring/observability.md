# EITP Multi-Tenant 可观测性埋点规范

## 日志注入标准

每条日志必须包含以下字段：

| 字段 | 来源 | 说明 |
|------|------|------|
| `tenant_id` | TenantContext | 租户标识，支持按租户检索 |
| `user_id` | TenantContext | 操作用户标识 |
| `trace_id` | 请求中间件 | 全链路追踪 ID |
| `timestamp` | structlog | ISO 8601 时间戳 |
| `level` | structlog | 日志级别 |
| `event` | structlog | 事件名称 |
| `error_code` | DomainError | `EITP_MT_*` 错误码 |

## 全链路追踪

```
API 层 (FastAPI middleware)
  → 应用层 (AppSvc)
    → 仓储层 (Repository)
      → 数据库 (SQLAlchemy)
```

每层注入 `trace_id`，支持按 `trace_id` 串联全链路。

## 租户级业务指标

| 指标 | 类型 | 说明 |
|------|------|------|
| `eitp_tenant_order_count` | Counter | 单据量（按 tenant_id） |
| `eitp_tenant_inventory_value` | Gauge | 库存价值（按 tenant_id） |
| `eitp_tenant_active_users` | Gauge | 活跃用户数（按 tenant_id） |
| `eitp_tenant_api_latency_ms` | Histogram | 接口耗时（按 tenant_id, endpoint） |

## 平台级运营指标

| 指标 | 类型 | 说明 |
|------|------|------|
| `eitp_platform_tenant_count` | Gauge | 活跃租户数 |
| `eitp_platform_resource_usage` | Gauge | 资源占用（CPU/内存/磁盘） |
| `eitp_tenant_context_resolution_ms` | Histogram | 租户上下文解析耗时 |
| `eitp_cross_company_summary_ms` | Histogram | 跨公司汇总耗时 |
| `eitp_cross_tenant_restore_denied_total` | Counter | 跨租户恢复拒绝次数 |
| `eitp_group_readonly_violation_total` | Counter | 集团只读违反次数 |