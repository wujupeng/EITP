# EITP INV-001 CI/CD 管线配置

## 构建管线

### 后端（FastAPI）
1. **lint**：`ruff check app/`
2. **type-check**：`mypy app/`
3. **unit-test**：`pytest tests/unit/ -v --cov=app/domain/inventory --cov-fail-under=90`
4. **build**：无编译步骤（Python 解释型）
5. **deploy**：rsync 到服务器 → pip install → alembic upgrade → restart uvicorn

### 前端（Vite + React）
1. **lint**：`eslint src/ --ext .ts,.tsx`
2. **type-check**：`tsc --noEmit`
3. **build**：`vite build` → `dist/`
4. **deploy**：rsync `dist/` 到服务器 nginx 静态目录

## Schema 迁移策略（向前兼容）

- Alembic 迁移 `010_inv_core_tables.py` 新增 15 个 `inv_*` 表，不影响存量 `mt_*` / `iam_*` 表
- 新增列允许 NULL，不修改存量列定义
- 新增表不影响存量数据
- 迁移顺序：MT-001(001-004) → IAM-001(005-009) → INV-001(010-019)

## 接口兼容性

- 新增 INV 接口前缀 `/api/v1/inv/`，不修改存量接口
- 新增错误码 `EITP_INV_*`，与 `EITP_MT_*` / `EITP_IAM_*` 并列共存
- 前端新增 `inventory/` 目录与路由，不影响存量页面

## 滚动升级策略

1. 执行 Alembic 迁移（向前兼容，可先迁移后部署）
2. 部署后端代码，重启 uvicorn
3. 部署前端构建产物到 nginx
4. 验证健康检查 `/health` 和黄金链路