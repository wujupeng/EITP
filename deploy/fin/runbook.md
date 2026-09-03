# EITP-FIN-001 Runbook - 财务与结算核心运维手册

## 1. 部署步骤

### 前置条件
- 11 个里程碑全部 FINAL PASS（Core Freeze 已生效）
- FIN-001 四条红线验证全部 PASS
- 775 个 FIN 测试全部通过
- 数据库迁移 070-079 已在目标环境执行
- FIN 配置种子（13 项 namespace=FIN）已加载至配置中心

### 部署操作
1. 执行 Alembic 迁移 070-079：`alembic upgrade head`
2. 加载 FIN 配置种子：`python deploy/batch_upload_mdm.py --seed deploy/fin/fin_config_seed.json`
3. 部署 Prometheus 抓取配置：`cp deploy/fin/prometheus.yml /etc/prometheus/conf.d/fin.yml`
4. 部署 Grafana 仪表盘：`cp deploy/fin/grafana_dashboard.yml /etc/grafana/provisioning/dashboards/fin.yml`
5. 重启 backend 服务并验证健康检查：`curl http://backend:8000/api/v1/fin/health`
6. 验证 7 项 Prometheus 指标已暴露：`curl http://backend:8000/metrics | grep eitp_fin_`

## 2. 健康检查

### 端点
| 端点 | 用途 |
|------|------|
| GET /api/v1/fin/health | FIN 域综合健康（银行回单/发票影像/事件总线） |
| GET /api/v1/fin/health/live | 存活检查 |
| GET /api/v1/fin/health/ready | 就绪检查（含数据库） |

### 健康状态
- `ok`：全部探测通过
- `degraded`：部分依赖不可用（银行回单接口/发票影像存储/事件总线订阅）

## 3. 告警处理

### 告警规则与处理
| 告警 | 指标 | 处理方式 |
|------|------|---------|
| 付款成功率低于 95% | eitp_fin_payment_success_rate < 0.95 | 检查银行接口连通性与付款渠道状态 |
| 对账差异数量激增 | eitp_fin_recon_diff_count > 100 | 执行对账差异排查，核对银行流水 |
| 资金池余额不足 | eitp_fin_treasury_balance < 阈值 | 触发资金调拨流程 |
| 应收账龄老化 | eitp_fin_ar_aging_bucket{bucket="180+"} 激增 | 启动催收流程（legal 阶段） |
| 发票开具失败 | eitp_fin_invoice_issued_total 增速骤降 | 检查税局接口与发票影像存储 |

## 4. 回滚方案

### 回滚步骤
1. 回滚 Alembic 迁移（降序执行 downgrade 079→070）
2. 回滚配置中心 FIN namespace 至前一快照
3. 回滚 backend 镜像至前一版本
4. 重启服务并验证健康检查

## 5. 四条红线监控

### 红线校验
| 红线 | 校验内容 | 验证测试 |
|------|---------|---------|
| Core Freeze | 11 个冻结聚合根不可变 | test_red_line_core_freeze.py |
| 只读引用 PUR/SAL | PurOrderReadView/SalOrderReadView 仅 SELECT | test_red_line_readonly_pur_sal.py |
| 财务域独立性 | FIN Bounded Context 独立 | test_red_line_finance_independence.py |
| 金额一致性 | Money 守恒 + DB CHECK 约束 | test_red_line_amount_consistency.py |

### 红线违规处理
- 任何红线违规立即阻断部署
- Core Freeze 违规触发 EITP_FIN_CORE_FREEZE_VIOLATION 错误码
- 红线违规写入审计日志（CORE_FREEZE_VIOLATED / FIN_CORE_FREEZE_VIOLATION）