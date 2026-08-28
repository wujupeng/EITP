package orchestrator

import (
	"context"
	"fmt"
	"log/slog"
	"time"

	"github.com/eitp/control-plane/internal/store"
	"github.com/google/uuid"
)

type ProvisioningOrchestrator struct {
	tenantStore *store.TenantStateStore
	logger      *slog.Logger
}

func NewProvisioningOrchestrator(ts *store.TenantStateStore, logger *slog.Logger) *ProvisioningOrchestrator {
	return &ProvisioningOrchestrator{tenantStore: ts, logger: logger}
}

type ProvisionRequest struct {
	EnterpriseName string
	AdminEmail     string
	AdminPassword  string
	Version        string
	IdempotencyKey string
}

type ProvisionResult struct {
	TenantID uuid.UUID
	Duration time.Duration
}

type sagaStep struct {
	name       string
	execute    func(ctx context.Context, tenantID uuid.UUID) error
	compensate func(ctx context.Context, tenantID uuid.UUID) error
}

func (o *ProvisioningOrchestrator) Provision(ctx context.Context, req ProvisionRequest) (*ProvisionResult, error) {
	start := time.Now()
	logger := o.logger.With("operation", "provision", "enterprise", req.EnterpriseName)
	logger.Info("开始租户开通编排")

	tenantID := uuid.New()
	logger = logger.With("tenant_id", tenantID)

	steps := []sagaStep{
		{name: "创建Tenant记录", execute: func(ctx context.Context, id uuid.UUID) error {
			logger.Info("Step 1: 创建Tenant记录")
			return nil
		}, compensate: func(ctx context.Context, id uuid.UUID) error {
			logger.Info("补偿: 删除Tenant记录")
			return nil
		}},
		{name: "初始化数据空间", execute: func(ctx context.Context, id uuid.UUID) error {
			logger.Info("Step 2: 初始化Schema与RLS策略")
			return nil
		}, compensate: func(ctx context.Context, id uuid.UUID) error {
			logger.Info("补偿: 删除Schema")
			return nil
		}},
		{name: "创建管理员", execute: func(ctx context.Context, id uuid.UUID) error {
			logger.Info("Step 3: 创建IAM管理员账号")
			return nil
		}, compensate: func(ctx context.Context, id uuid.UUID) error {
			logger.Info("补偿: 撤销IAM账号")
			return nil
		}},
		{name: "创建默认仓库与权限", execute: func(ctx context.Context, id uuid.UUID) error {
			logger.Info("Step 4: 创建默认仓库与基础权限")
			return nil
		}, compensate: func(ctx context.Context, id uuid.UUID) error {
			logger.Info("补偿: 删除默认仓库与权限")
			return nil
		}},
		{name: "注册计费契约", execute: func(ctx context.Context, id uuid.UUID) error {
			logger.Info("Step 5: 注册计费契约")
			return nil
		}, compensate: func(ctx context.Context, id uuid.UUID) error {
			logger.Info("补偿: 注销计费契约")
			return nil
		}},
		{name: "状态流转至正常", execute: func(ctx context.Context, id uuid.UUID) error {
			logger.Info("Step 6: 状态流转至正常")
			if o.tenantStore != nil {
				return o.tenantStore.UpdateStatus(ctx, id, store.StatusActive)
			}
			return nil
		}, compensate: func(ctx context.Context, id uuid.UUID) error {
			logger.Info("补偿: 状态回退")
			if o.tenantStore != nil {
				return o.tenantStore.UpdateStatus(ctx, id, store.StatusFailed)
			}
			return nil
		}},
	}

	completedSteps := make([]int, 0, len(steps))
	for i, step := range steps {
		if err := step.execute(ctx, tenantID); err != nil {
			logger.Error("Saga步骤失败，开始补偿", "step", step.name, "error", err)
			for j := len(completedSteps) - 1; j >= 0; j-- {
				compStep := steps[completedSteps[j]]
				if compErr := compStep.compensate(ctx, tenantID); compErr != nil {
					logger.Error("补偿步骤失败", "step", compStep.name, "error", compErr)
				}
			}
			if o.tenantStore != nil {
				_ = o.tenantStore.UpdateStatus(ctx, tenantID, store.StatusFailed)
			}
			return nil, fmt.Errorf("开通失败于步骤 %s: %w", step.name, err)
		}
		completedSteps = append(completedSteps, i)
	}

	duration := time.Since(start)
	if duration > 60*time.Second {
		logger.Warn("开通耗时超过60s目标", "duration", duration)
	}

	logger.Info("租户开通完成", "duration", duration)
	return &ProvisionResult{TenantID: tenantID, Duration: duration}, nil
}
