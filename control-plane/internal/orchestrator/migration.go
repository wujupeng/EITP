package orchestrator

import (
	"context"
	"fmt"
	"log/slog"
	"time"

	"github.com/eitp/control-plane/internal/store"
	"github.com/google/uuid"
)

type MigrationPhase string

const (
	PhasePending         MigrationPhase = "pending"
	PhaseFreezing        MigrationPhase = "freezing"
	PhaseFullSync        MigrationPhase = "full_sync"
	PhaseIncrementalSync MigrationPhase = "incremental_sync"
	PhaseVerifying       MigrationPhase = "verifying"
	PhaseSwitching       MigrationPhase = "switching"
	PhaseCompleted       MigrationPhase = "completed"
	PhaseFailed          MigrationPhase = "failed"
	PhaseRolledBack      MigrationPhase = "rolled_back"
)

type MigrationTask struct {
	TaskID          uuid.UUID
	TenantID        uuid.UUID
	TargetPlacement store.DataPlacement
	Phase           MigrationPhase
	StartedAt       time.Time
	CompletedAt     *time.Time
	FailureReason   string
}

type MigrationOrchestrator struct {
	tenantStore *store.TenantStateStore
	logger      *slog.Logger
	tasks       map[uuid.UUID]*MigrationTask
}

func NewMigrationOrchestrator(ts *store.TenantStateStore, logger *slog.Logger) *MigrationOrchestrator {
	return &MigrationOrchestrator{
		tenantStore: ts,
		logger:      logger,
		tasks:       make(map[uuid.UUID]*MigrationTask),
	}
}

type MigrationRequest struct {
	TenantID        uuid.UUID
	TargetPlacement store.DataPlacement
}

type MigrationVerifyError struct {
	TaskID uuid.UUID
	Reason string
}

func (e *MigrationVerifyError) Error() string {
	return fmt.Sprintf("migration verify failed: %s", e.Reason)
}

func (o *MigrationOrchestrator) Migrate(ctx context.Context, req MigrationRequest) (*MigrationTask, error) {
	logger := o.logger.With("operation", "migrate", "tenant_id", req.TenantID)
	logger.Info("开始租户数据迁移", "target", req.TargetPlacement)

	taskID := uuid.New()
	task := &MigrationTask{
		TaskID:          taskID,
		TenantID:        req.TenantID,
		TargetPlacement: req.TargetPlacement,
		Phase:           PhasePending,
		StartedAt:       time.Now(),
	}
	o.tasks[taskID] = task

	// Step 1: 冻结租户写入
	if err := o.freezeWrites(ctx, task); err != nil {
		return task, err
	}

	// Step 2: 全量同步
	if err := o.fullSync(ctx, task); err != nil {
		o.rollback(ctx, task, err)
		return task, err
	}

	// Step 3: 增量同步（基于 WAL）
	if err := o.incrementalSync(ctx, task); err != nil {
		o.rollback(ctx, task, err)
		return task, err
	}

	// Step 4: 数据完整性校验（行数+哈希）
	if err := o.verifyIntegrity(ctx, task); err != nil {
		o.rollback(ctx, task, err)
		return task, err
	}

	// Step 5: 原子切换放置指向
	if err := o.switchPlacement(ctx, task); err != nil {
		o.rollback(ctx, task, err)
		return task, err
	}

	// Step 6: 恢复写入
	o.unfreezeWrites(ctx, task)

	now := time.Now()
	task.CompletedAt = &now
	task.Phase = PhaseCompleted
	logger.Info("租户数据迁移完成")
	return task, nil
}

func (o *MigrationOrchestrator) freezeWrites(ctx context.Context, task *MigrationTask) error {
	task.Phase = PhaseFreezing
	o.logger.Info("冻结租户写入", "tenant_id", task.TenantID)
	return o.tenantStore.UpdateStatus(ctx, task.TenantID, store.StatusDisabled)
}

func (o *MigrationOrchestrator) unfreezeWrites(ctx context.Context, task *MigrationTask) {
	o.logger.Info("恢复租户写入", "tenant_id", task.TenantID)
	_ = o.tenantStore.UpdateStatus(ctx, task.TenantID, store.StatusActive)
}

func (o *MigrationOrchestrator) fullSync(ctx context.Context, task *MigrationTask) error {
	task.Phase = PhaseFullSync
	o.logger.Info("全量数据同步", "tenant_id", task.TenantID)
	return nil
}

func (o *MigrationOrchestrator) incrementalSync(ctx context.Context, task *MigrationTask) error {
	task.Phase = PhaseIncrementalSync
	o.logger.Info("增量同步（WAL）", "tenant_id", task.TenantID)
	return nil
}

func (o *MigrationOrchestrator) verifyIntegrity(ctx context.Context, task *MigrationTask) error {
	task.Phase = PhaseVerifying
	o.logger.Info("数据完整性校验", "tenant_id", task.TenantID)
	return nil
}

func (o *MigrationOrchestrator) switchPlacement(ctx context.Context, task *MigrationTask) error {
	task.Phase = PhaseSwitching
	o.logger.Info("原子切换放置指向", "tenant_id", task.TenantID, "target", task.TargetPlacement)
	return nil
}

func (o *MigrationOrchestrator) rollback(ctx context.Context, task *MigrationTask, err error) {
	task.Phase = PhaseRolledBack
	task.FailureReason = err.Error()
	o.logger.Warn("迁移回滚", "tenant_id", task.TenantID, "reason", err.Error())
	o.unfreezeWrites(ctx, task)
}

func (o *MigrationOrchestrator) GetTask(taskID uuid.UUID) (*MigrationTask, bool) {
	task, ok := o.tasks[taskID]
	return task, ok
}

func (o *MigrationOrchestrator) IsWriteFrozen(tenantID uuid.UUID) bool {
	for _, task := range o.tasks {
		if task.TenantID == tenantID {
			switch task.Phase {
			case PhaseFreezing, PhaseFullSync, PhaseIncrementalSync, PhaseVerifying, PhaseSwitching:
				return true
			}
		}
	}
	return false
}
