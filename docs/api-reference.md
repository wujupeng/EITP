# EITP Multi-Tenant API Reference

> Base URL: `/api/v1`
> 认证: `X-Tenant-Token` 请求头（UUID 格式租户令牌）
> 错误码前缀: `EITP_MT_*`

## 接口清单

### 1. 租户管理（平台运营）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/platform/tenants` | 开通新租户 |
| GET | `/platform/tenants` | 列出所有租户 |
| GET | `/platform/tenants/{tenant_id}` | 查询单个租户 |
| POST | `/platform/tenants/{tenant_id}/status` | 租户状态流转（停用/恢复/注销） |

**开通租户** `POST /platform/tenants`

```json
{
  "enterprise_name": "示例企业",
  "idempotency_key": "idem-001",
  "admin_email": "admin@example.com",
  "data_placement": "shared_db"
}
```

**状态流转** `POST /platform/tenants/{tenant_id}/status`

```json
{"action": "disable"}
{"action": "enable"}
{"action": "deprovision", "confirm_token": "{tenant_id}"}
```

### 2. 层级管理（租户管理员）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/tenant/hierarchy/nodes` | 创建层级节点 |
| GET | `/tenant/hierarchy/nodes/{node_id}` | 查询节点 |
| GET | `/tenant/hierarchy/tree` | 查询层级树 |
| PATCH | `/tenant/hierarchy/nodes/{node_id}/disable` | 停用节点（级联） |

层级类型：1=Platform, 2=Tenant, 3=Enterprise, 4=Organization, 5=Site, 6=Warehouse, 7=Location

### 3. 配置管理（租户管理员）

| 方法 | 路径 | 说明 |
|------|------|------|
| PATCH | `/tenant/config/values` | 设置配置项（显式覆盖） |
| GET | `/tenant/config/values/{config_key}` | 查询配置项（含继承求值） |
| PATCH | `/tenant/config/feature-flags` | 设置功能开关 |
| GET | `/tenant/config/feature-flags/{feature_key}` | 查询功能开关 |

### 4. 集团报表（集团管理员）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/group/reports/{dimension}` | 查询集团汇总报表 |
| POST | `/group/master-data:propagate` | 下发集团主数据 |
| POST | `/group/snapshots` | 更新汇总快照 |
| POST | `/group/readonly-check` | 只读边界校验 |

报表维度：`sales`、`inventory`、`procurement`

### 5. 主数据管理（集团/租户管理员）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/master-data/sku` | 创建 SKU 基准 |
| PUT | `/master-data/sku/{sku_id}` | 更新 SKU 基准（集团管理员） |
| PUT | `/master-data/sku/{sku_id}/company-override` | 设置公司级覆盖 |
| PUT | `/master-data/sku/{sku_id}/warehouse-override` | 设置仓库级覆盖 |
| GET | `/master-data/sku/{sku_id}/effective` | 查询生效值（三层合并） |

### 6. 放置与迁移（平台运营）

| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | `/platform/placement/{tenant_id}` | 切换放置模式 |
| GET | `/platform/placement/{tenant_id}` | 查询放置记录 |
| POST | `/platform/placement/{tenant_id}/migrate` | 发起迁移 |
| GET | `/platform/placement/{tenant_id}/migrate/{task_id}/status` | 查询迁移状态 |

放置模式：`shared_db`、`dedicated_db`、`dedicated_instance`

### 7. 备份与恢复（平台运营）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/platform/backup/{tenant_id}` | 触发租户备份 |
| GET | `/platform/backup/{tenant_id}/list` | 查询备份列表 |
| POST | `/platform/backup/{backup_id}/restore` | 恢复备份 |
| PUT | `/platform/backup/{tenant_id}/retention` | 设置保留策略 |

## 错误码

| 错误码 | HTTP | 说明 |
|--------|------|------|
| `EITP_MT_TENANT_CONTEXT_INVALID` | 401 | 租户令牌非法/缺失 |
| `EITP_MT_TENANT_ALREADY_EXISTS` | 409 | 租户已存在（幂等键重复） |
| `EITP_MT_TENANT_CANCEL_CONFIRMATION_REQUIRED` | 422 | 注销需二次确认 |
| `EITP_MT_HIERARCHY_CROSS_TENANT` | 422 | 跨租户层级操作 |
| `EITP_MT_GROUP_READONLY_VIOLATION` | 403 | 集团只读边界违反 |
| `EITP_MT_GROUP_SNAPSHOT_DELAYED` | 200 | 汇总快照延迟（is_delayed=true） |
| `EITP_MT_MASTER_BASE_READONLY` | 422 | 集团基准只读 |
| `EITP_MT_MASTER_ATTR_CONFLICT` | 409 | 主数据属性冲突 |
| `EITP_MT_MASTER_NOT_FOUND` | 404 | 主数据不存在 |
| `EITP_MT_MASTER_DATA_CONFLICT` | 409 | 主数据下发冲突 |
| `EITP_MT_MASTER_PROPAGATE_FAILED` | 500 | 主数据下发失败 |
| `EITP_MT_SUBSIDIARY_ISOLATION_VIOLATION` | 403 | 子公司隔离违反 |
| `EITP_MT_MIGRATION_VERIFY_FAILED` | 500 | 迁移校验失败 |
| `EITP_MT_MIGRATION_TIMEOUT` | 408 | 迁移超时 |
| `EITP_MT_PLACEMENT_RESOURCE_INSUFFICIENT` | 503 | 放置资源不足 |
| `EITP_MT_BACKUP_CORRUPTED` | 500 | 备份文件损坏 |
| `EITP_MT_BACKUP_STORAGE_INSUFFICIENT` | 507 | 备份存储不足 |
| `EITP_MT_CROSS_TENANT_RESTORE_DENIED` | 403 | 跨租户恢复拒绝 |
| `EITP_MT_RESTORE_FAILED` | 500 | 恢复失败 |

## 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 完整健康检查 |
| GET | `/health/live` | 存活探针 |
| GET | `/health/ready` | 就绪探针 |