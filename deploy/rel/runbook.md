# EITP-REL-001 Runbook - 生产封版与核心冻结运维手册

## 1. 发起封版流程

### 前置条件
- 10 个里程碑全部 FINAL PASS
- 378 项回归测试全部通过
- Git 工作区干净（无未提交变更）
- SEC 证书与 PROD 证明书在有效期内

### 操作步骤
1. 登录前端 → 导航至「封版管理」→「发起封版」
2. 填写封版编号（REL-YYYY-NNN）、版本号（1.0.0）、Git Tag（v1.0.0）
3. 提交封版请求 → 系统自动执行 6 项门禁
4. 门禁全通过后 → 系统自动采集 14 项资产快照
5. 快照采集完成 → 系统自动汇编封版报告
6. 报告汇编完成 → 等待联合签发
7. 发布经理 + 安全负责人分别签发 → 封版完成（SEALED）

## 2. 门禁失败处理

### 门禁类型与错误码
| 门禁 | 错误码 | 处理方式 |
|------|--------|---------|
| 里程碑 FINAL PASS | EITP_REL_GATE_MILESTONE_NOT_PASS | 检查对应里程碑 review.md |
| Core Freeze 哈希 | EITP_REL_GATE_CORE_TAMPERED | 检查核心资产是否被篡改 |
| 378 回归 | EITP_REL_GATE_REGRESSION_FAILED | 修复失败测试用例 |
| Git 工作区 | EITP_REL_GATE_DIRTY_WORKTREE | 提交或 stash 未提交变更 |
| Git Tag 冲突 | EITP_REL_GATE_TAG_EXISTS | 选择新的 Git Tag 名称 |
| 证书有效期 | EITP_REL_GATE_CERT_INVALID | 续期 SEC 证书或重新签发 PROD 证明书 |

### 重试门禁
门禁失败后可重试指定门禁：
```
POST /api/v1/rel/gates/{release_id}/retry
{"gate_types": ["REGRESSION_378"], "executed_by": "release-manager"}
```

## 3. 联合签发

### 签发要求
- 发布经理（RELEASE_MANAGER 角色）+ 安全负责人（SECURITY_OFFICER 角色）
- 双方必须为不同人员（防代签）
- 双方凭证经 IAM 角色校验

### 签发操作
```
POST /api/v1/rel/seals/{release_id}/co-sign
{"releaser": "release-manager", "security_officer": "security-officer"}
```

## 4. 回滚方案

### 回滚步骤
1. 回滚 Git Tag 至前一版本
2. 回滚 Alembic 迁移（降序执行 downgrade 069→065）
3. 回滚配置中心至前一 namespace 快照
4. 重启服务并验证健康检查

### 回滚演练
在隔离环境执行回滚演练：
```
POST /api/v1/rel/rollback-plans/{release_id}/drill
{"drill_result": {"environment": "staging"}}
```

## 5. 解冻流程（仅限紧急情况）

### 解冻审批流程
1. 提交解冻申请（UNFREEZE_REQUESTED）
2. 发布经理审批
3. 安全负责人审批
4. CTO 审批
5. 执行解冻（REVOKED）

### 注意事项
- 解冻后原冻结声明不可恢复
- 解冻需重新执行封版流程
- 解冻操作写入审计日志