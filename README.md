# EITP Multi-Tenant

> **多企业统一进销存交易平台** — 参照 Oracle Simphony 层级模型的多租户 SaaS 平台，一套代码承载 N 家企业独立运行。

---

## 目录

- [项目概述](#项目概述)
- [核心特性](#核心特性)
- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [部署指南](#部署指南)
- [API 文档](#api-文档)
- [测试](#测试)
- [CI/CD](#cicd)
- [监控与可观测性](#监控与可观测性)
- [运维手册](#运维手册)
- [里程碑评审](#里程碑评审)

---

## 项目概述

EITP（Enterprise Inventory & Trade Platform）是一个面向多企业的统一进销存交易 SaaS 平台。平台参照 Oracle Simphony 的七层组织层级模型，通过 DDD（领域驱动设计）方法论构建，支持从平台运营到租户业务的完整生命周期管理。

### 七层组织层级

```
Platform → Tenant → Enterprise → Organization → Site → Warehouse → Location
  ①         ②         ③            ④            ⑤        ⑥           ⑦
```

| 层级 | 说明 | 管理角色 |
|------|------|----------|
| Platform | 平台运营方 | 平台管理员 |
| Tenant | 租户（企业集团） | 租户管理员 |
| Enterprise | 企业法人 | 集团管理员 |
| Organization | 组织/子公司 | 组织管理员 |
| Site | 站点/门店 | 站点管理员 |
| Warehouse | 仓库 | 仓库管理员 |
| Location | 库位 | 库位管理员 |

### 三种数据放置模式

| 模式 | 隔离级别 | 适用场景 |
|------|----------|----------|
| `shared_db` | 行级隔离（RLS） | 中小租户、成本最优 |
| `dedicated_db` | 数据库级隔离 | 中等规模、合规需求 |
| `dedicated_instance` | 实例级物理隔离 | 大型企业、SLA 独立 |

---

## 核心特性

### 1. 多租户隔离

- **四层纵深隔离**：令牌校验 → 租户状态校验 → 数据范围限制 → 跨租户操作拒绝
- **租户上下文**：通过 `X-Tenant-Token` 头注入，贯穿请求生命周期
- **DataScope 守卫**：自动注入查询过滤，防止跨租户数据泄漏

### 2. 集团模式与跨公司报表

- 集团管理员只读边界（`SubsidiaryIsolationGuard`）
- 跨公司汇总报表（支持 sales/inventory/procurement 维度）
- 汇总快照 + 延迟标记（`is_delayed`，超 5 分钟标记）
- 集团主数据下发至子公司

### 3. 主数据层级继承

- 三层合并求值：集团基准 → 公司级覆盖 → 仓库级覆盖
- 权限守卫：子公司管理员不可修改集团基准
- 属性级覆盖（`CompanyOverride` / `WarehouseOverride`）
- 下发冲突检测与暂停

### 4. 数据放置与迁移

- 四阶段迁移编排：冻结 → 全量同步 → 增量同步 → 校验切换
- 行数 + 哈希双重校验
- 大客户迁移建议评估
- 完整回滚机制

### 5. 租户备份与恢复

- 租户级备份触发与恢复
- 跨租户恢复拒绝（`CROSS_TENANT_RESTORE_DENIED`）
- 保留策略（按数量/时间）
- 故障隔离（C-RELI-01）+ 恢复时效（C-RELI-02 ≤15min）

### 6. 存量数据迁移

- PHP 系统数据适配器（`LegacyMigrationAdapter` 契约）
- ETL 工具（提取-转换-加载）
- 迁移校验器（行数 + 哈希）
- 迁移进度追踪

### 7. 配置开关与继承

- 配置项层级继承求值（`ConfigResolver`）
- 功能开关（`FeatureFlag`）即时生效
- 缓存失效机制
- 显式覆盖与继承求值

### 8. 业务规则引擎

- 审批阈值配置
- 多级审批流
- 规则优先级与冲突解决

---

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React + Ant Design)          │
│                    Nginx / CDN                            │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS
┌────────────────────────┴────────────────────────────────┐
│              Application Plane (FastAPI / Python)         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ Hierarchy │ │  Tenant  │ │  Config  │ │  Rules   │   │
│  │    BC     │ │    BC    │ │    BC    │ │    BC    │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │  Group   │ │MasterData│ │Placement │ │  Backup  │   │
│  │    BC    │ │    BC    │ │    BC    │ │    BC    │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────┐
│              Control Plane (Go)                           │
│  租户开通 Saga | 迁移编排 | 备份编排 | 放置管理          │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────┐
│  PostgreSQL (shared/dedicated)  │  Redis  │  Rust Agent  │
│  Alembic Schema Migration       │  Cache  │  Backup/Mig  │
└─────────────────────────────────────────────────────────┘
```

### DDD 分层

```
interfaces/        # API 路由、Schema、中间件
  └── api/v1/      # RESTful 接口
  └── middleware/  # 租户上下文、错误处理、功能开关守卫
  └── schemas/     # Pydantic 请求/响应模型
application/       # 应用服务（编排领域层与仓储层）
domain/            # 聚合根、实体、值对象、领域事件、仓储接口
infrastructure/    # 仓储实现、ORM 模型、数据库会话
```

---

## 技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| **应用面** | FastAPI + SQLAlchemy async + Pydantic | Python 3.10+ |
| **控制面** | Go + pgx | Go 1.22 |
| **前端** | React + TypeScript + Ant Design + ECharts + Vite | React 18, Vite 6.4 |
| **数据库** | PostgreSQL | 16 |
| **缓存** | Redis | 7 |
| **Agent** | Rust（备份/迁移数据流） | - |
| **CI/CD** | GitHub Actions | - |
| **监控** | Prometheus + Grafana + Loki | - |
| **容器** | Docker + Docker Compose | - |

---

## 项目结构

```
EITP/
├── backend/                    # 应用面 FastAPI
│   ├── app/
│   │   ├── domain/             # 领域层（9 个 Bounded Context）
│   │   │   ├── hierarchy/      # 层级 BC
│   │   │   ├── tenant/         # 租户 BC
│   │   │   ├── config/         # 配置 BC
│   │   │   ├── rules/          # 业务规则 BC
│   │   │   ├── audit/          # 审计 BC
│   │   │   ├── group/          # 集团 BC
│   │   │   ├── masterdata/     # 主数据 BC
│   │   │   ├── placement/      # 放置 BC
│   │   │   ├── backup/         # 备份 BC
│   │   │   └── legacy_migration/  # 存量迁移 BC
│   │   ├── application/        # 应用服务层
│   │   ├── infrastructure/     # 基础设施层
│   │   └── interfaces/         # 接口层
│   ├── alembic/                # 数据库迁移
│   ├── tests/                  # 测试（unit + integration + e2e + dfx）
│   └── pyproject.toml
├── control-plane/              # 控制面 Go
│   ├── cmd/server/             # 入口
│   ├── internal/
│   │   ├── auth/               # 认证
│   │   ├── orchestrator/       # 编排（迁移/备份/放置）
│   │   └── store/              # 数据访问
│   └── api/                    # HTTP handler
├── frontend/                   # 前端 React
│   ├── src/
│   │   ├── pages/              # 页面组件
│   │   ├── router/             # 路由
│   │   └── services/           # API 调用
│   └── package.json
├── rust-agent/                 # Rust Agent（备份/迁移）
├── deploy/                     # 部署配置
│   ├── docker/                 # Dockerfile + nginx
│   ├── docker-compose.*.yml    # 三种部署模式
│   └── monitoring/             # Prometheus + 告警
├── docs/                       # 文档
│   ├── api-reference.md        # API 接口文档
│   ├── operations-manual.md    # 运维手册
│   └── milestone-review.md     # 里程碑评审报告
└── .github/workflows/ci.yml    # CI/CD 管线
```

---

## 快速开始

### 前置条件

- Python 3.10+
- Go 1.22+
- Node.js 22+
- PostgreSQL 16+
- Redis 7+

### 本地开发

**1. 启动数据库**

```bash
docker run -d --name eitp-pg \
  -e POSTGRES_DB=eitp_dev \
  -e POSTGRES_USER=eitp \
  -e POSTGRES_PASSWORD=eitp_dev \
  -p 5432:5432 postgres:16-alpine

docker run -d --name eitp-redis -p 6379:6379 redis:7-alpine
```

**2. 启动后端**

```bash
cd backend
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**3. 启动控制面**

```bash
cd control-plane
go run ./cmd/server
```

**4. 启动前端**

```bash
cd frontend
npm install
npm run dev
```

**5. 访问应用**

- 前端：http://localhost:5173
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

---

## 部署指南

### 共享数据库模式

```bash
docker compose -f deploy/docker-compose.shared.yml up -d
```

### 独立数据库模式

```bash
docker compose -f deploy/docker-compose.dedicated.yml up -d
```

### 独立实例模式

```bash
export TENANT_A_ID="uuid-of-tenant-a"
export TENANT_B_ID="uuid-of-tenant-b"
docker compose -f deploy/docker-compose.dedicated-instance.yml up -d
```

详细部署说明参见 [运维手册](docs/operations-manual.md)。

---

## API 文档

完整 API 文档参见 [API Reference](docs/api-reference.md)。

### 快速概览

| 模块 | 路径前缀 | 说明 |
|------|----------|------|
| 租户管理 | `/api/v1/platform/tenants` | 开通/停用/恢复/注销 |
| 层级管理 | `/api/v1/tenant/hierarchy` | 7 层组织树 |
| 配置管理 | `/api/v1/tenant/config` | 配置项 + 功能开关 |
| 集团报表 | `/api/v1/group` | 跨公司汇总 + 主数据下发 |
| 主数据 | `/api/v1/master-data` | 三层继承 + 覆盖 |
| 放置迁移 | `/api/v1/platform/placement` | 模式切换 + 迁移编排 |
| 备份恢复 | `/api/v1/platform/backup` | 备份 + 恢复 + 保留策略 |

认证方式：`X-Tenant-Token` 请求头（UUID 格式）

---

## 测试

### 运行测试

```bash
# 后端全量测试
cd backend
python -m pytest tests/ -v

# 控制面测试
cd control-plane
go test ./... -v

# 前端类型检查
cd frontend
npm run typecheck
```

### 测试统计

| 类型 | 数量 | 说明 |
|------|------|------|
| Python 单元测试 | 246 | 领域模型 + 应用服务 + API |
| Python 集成测试 | 11 | 跨模块隔离穿透 |
| E2E 测试 | 17 + 4 skipped | 三大角色全路径 |
| DFX 测试 | 6 + 7 skipped | 性能/安全/可靠性 |
| Go 测试 | 12 | 编排器 + 认证 |
| 前端 typecheck | 0 errors | TypeScript 编译检查 |
| **合计** | **274 passed, 11 skipped** | skipped 需 CI 环境工具 |

---

## CI/CD

GitHub Actions 管线（`.github/workflows/ci.yml`）包含：

1. **后端**：ruff lint → mypy → pytest → coverage
2. **控制面**：go vet → go test → go build
3. **前端**：npm ci → typecheck → build
4. **Docker**：构建三组件镜像（main 分支）
5. **迁移检查**：alembic upgrade + alembic check

---

## 监控与可观测性

### 关键指标

| 指标 | 阈值 | 告警 |
|------|------|------|
| 租户上下文解析 | ≤20ms | warning |
| 业务查询 P95 | ≤500ms | warning |
| 跨公司汇总 | ≤3s | warning |
| 租户开通 | ≤60s | warning |
| 后端可用性 | 99.9% | critical |

### 日志标准

每条日志包含：`tenant_id`、`user_id`、`trace_id`、`timestamp`、`level`、`event`、`error_code`

详细配置参见 [监控文档](deploy/monitoring/observability.md)。

---

## 运维手册

完整运维手册参见 [Operations Manual](docs/operations-manual.md)，覆盖：

- 三种部署模式详解
- 数据放置迁移流程
- 备份恢复流程
- 统一升级策略
- 监控告警配置
- 故障处理指南

---

## 里程碑评审

里程碑评审报告参见 [Milestone Review](docs/milestone-review.md)。

### 评审结论

- ✅ 14 个任务组全部完成
- ✅ 9 大核心能力模块全覆盖
- ✅ 274 测试通过
- ✅ 5 项关键风险全部闭环
- ✅ DDD 分层合规，无贫血模型
- ✅ 四层纵深隔离完整
- ✅ API 向后兼容策略已定义

---

## 错误码

所有错误码使用 `EITP_MT_*` 前缀，完整列表参见 [API Reference](docs/api-reference.md#错误码)。

| 错误码 | HTTP | 说明 |
|--------|------|------|
| `EITP_MT_TENANT_CONTEXT_INVALID` | 401 | 租户令牌非法/缺失 |
| `EITP_MT_GROUP_READONLY_VIOLATION` | 403 | 集团只读边界违反 |
| `EITP_MT_CROSS_TENANT_RESTORE_DENIED` | 403 | 跨租户恢复拒绝 |
| `EITP_MT_MASTER_BASE_READONLY` | 422 | 集团基准只读 |
| `EITP_MT_TENANT_CANCEL_CONFIRMATION_REQUIRED` | 422 | 注销需二次确认 |
| ... | ... | 完整列表见 API 文档 |

---

## License

Private - All Rights Reserved