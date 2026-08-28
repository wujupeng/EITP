# EITP Multi-Tenant 运维手册

## 1. 部署模式

### 1.1 共享数据库模式（shared_db）

**适用场景**：中小租户、快速开通、成本最优

**部署拓扑**：
- 单 PostgreSQL 实例，所有租户共享
- 通过 RLS（Row Level Security）实现行级隔离
- 单后端实例，通过 TenantContext 中间件隔离

**部署命令**：
```bash
docker compose -f deploy/docker-compose.shared.yml up -d
```

**升级策略**：滚动升级后端实例，数据库 Schema 向前兼容迁移

### 1.2 独立数据库模式（dedicated_db）

**适用场景**：中等规模租户、数据隔离要求高、合规需求

**部署拓扑**：
- 控制面数据库（租户元数据、放置记录）
- 每租户独立 PostgreSQL 数据库
- 连接路由器按 tenant_id 分发

**部署命令**：
```bash
docker compose -f deploy/docker-compose.dedicated.yml up -d
```

**升级策略**：按租户逐个迁移 Schema，升级过程不影响其他租户

### 1.3 独立实例模式（dedicated_instance）

**适用场景**：大型企业、强合规需求、SLA 独立保障

**部署拓扑**：
- 控制面独立部署
- 每租户独立 PostgreSQL 实例 + 独立后端实例
- 网关按 tenant_id 路由到对应后端

**部署命令**：
```bash
export TENANT_A_ID="uuid-of-tenant-a"
export TENANT_B_ID="uuid-of-tenant-b"
docker compose -f deploy/docker-compose.dedicated-instance.yml up -d
```

**升级策略**：按租户独立升级，零影响其他租户

## 2. 迁移流程

### 2.1 数据放置迁移（shared_db → dedicated_db）

1. **评估**：调用 `GET /platform/placement/{tenant_id}` 评估迁移建议
2. **冻结**：控制面冻结源库写入（`POST /platform/placement/{tenant_id}/migrate`）
3. **全量同步**：Rust Agent 执行全量数据复制
4. **增量同步**：解除冻结，持续增量同步
5. **校验**：行数 + 哈希校验
6. **切换**：维护窗口内切换连接路由
7. **恢复**：验证完成后恢复写入

### 2.2 回滚

若校验失败或切换异常：
1. 连接路由回退至源库
2. 恢复源库写入
3. 标记迁移任务为 `rolled_back`
4. 审计记录回滚事件

## 3. 备份恢复流程

### 3.1 触发备份

```bash
curl -X POST http://localhost:8000/api/v1/platform/backup/{tenant_id} \
  -H "X-Tenant-Token: {admin_token}"
```

### 3.2 恢复备份

```bash
curl -X POST http://localhost:8000/api/v1/platform/backup/{backup_id}/restore \
  -H "X-Tenant-Token: {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{"target_tenant_id": "{same_tenant_id}"}'
```

**注意**：跨租户恢复被拒绝（`EITP_MT_CROSS_TENANT_RESTORE_DENIED`）

### 3.3 保留策略

```bash
curl -X PUT http://localhost:8000/api/v1/platform/backup/{tenant_id}/retention \
  -H "X-Tenant-Token: {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{"max_count": 30, "max_age_days": 90}'
```

## 4. 统一升级流程

### 4.1 应用面升级（滚动）

1. 新版本镜像推送至镜像仓库
2. `docker compose up -d --no-deps backend` 触发滚动升级
3. 健康检查通过后旧实例下线
4. API 向后兼容（C-COMPAT-01），升级过程对租户透明

### 4.2 控制面升级（独立）

1. 控制面独立部署，不影响业务请求
2. `docker compose up -d --no-deps control-plane`
3. 升级期间控制面 API 短暂不可用（<5s）

### 4.3 数据库 Schema 迁移

```bash
# 共享模式：单次迁移
alembic upgrade head

# 独立数据库模式：按租户逐个迁移
for tenant_db in tenant_a tenant_b tenant_c; do
  DB_URL="postgresql+asyncpg://eitp:pwd@postgres:5432/$tenant_db" alembic upgrade head
done
```

**向前兼容原则**：Schema 变更必须向前兼容，先部署新版本代码（兼容旧 Schema），再迁移 Schema

## 5. 监控与告警

### 5.1 关键指标

| 指标 | 阈值 | 告警 |
|------|------|------|
| 租户上下文解析 | ≤20ms | warning |
| 业务查询 P95 | ≤500ms | warning |
| 跨公司汇总 | ≤3s | warning |
| 租户开通 | ≤60s | warning |
| 后端可用性 | 99.9% | critical |

### 5.2 安全告警

| 事件 | 告警级别 |
|------|----------|
| 跨租户恢复尝试 | critical |
| 集团只读边界违反 | warning |
| 无令牌访问 | info（审计） |

## 6. 故障处理

### 6.1 租户故障隔离（C-RELI-01）

- 单租户故障不跨租户传播
- 独立实例模式：单租户实例宕机不影响其他租户
- 共享数据库模式：通过 TenantContext 隔离，单租户数据异常不影响其他租户

### 6.2 单租户恢复（C-RELI-02）

- 目标：≤15 分钟
- 流程：识别故障 → 恢复备份 → 验证数据 → 恢复服务