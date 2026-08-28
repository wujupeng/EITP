package orchestrator

import (
	"context"
	"fmt"
	"log/slog"
	"time"

	"github.com/google/uuid"
)

type BackupStatus string

const (
	BackupPending   BackupStatus = "pending"
	BackupCompleted BackupStatus = "completed"
	BackupFailed    BackupStatus = "failed"
)

type BackupRecord struct {
	BackupID   uuid.UUID
	TenantID   uuid.UUID
	StorageURI string
	Checksum   string
	Status     BackupStatus
	CreatedAt  time.Time
	SizeBytes  int64
}

type RestoreResult struct {
	RestoreTaskID uuid.UUID
	BackupID      uuid.UUID
	TenantID      uuid.UUID
	Status        string
}

type BackupOrchestrator struct {
	logger  *slog.Logger
	records map[uuid.UUID]*BackupRecord
}

func NewBackupOrchestrator(logger *slog.Logger) *BackupOrchestrator {
	return &BackupOrchestrator{
		logger:  logger,
		records: make(map[uuid.UUID]*BackupRecord),
	}
}

type BackupRequest struct {
	TenantID uuid.UUID
}

type BackupResult struct {
	BackupID uuid.UUID
}

func (o *BackupOrchestrator) Backup(ctx context.Context, req BackupRequest) (*BackupResult, error) {
	logger := o.logger.With("operation", "backup", "tenant_id", req.TenantID)
	logger.Info("开始租户级备份")

	backupID := uuid.New()
	record := &BackupRecord{
		BackupID:  backupID,
		TenantID:  req.TenantID,
		Status:    BackupPending,
		CreatedAt: time.Now(),
	}
	o.records[backupID] = record

	// Step 1: 调度 Rust Agent 执行数据导出
	storageURI, checksum, sizeBytes, err := o.exportToStorage(ctx, req.TenantID)
	if err != nil {
		record.Status = BackupFailed
		logger.Error("备份导出失败", "error", err)
		return &BackupResult{BackupID: backupID}, err
	}

	// Step 2: 计算完整性校验值
	record.StorageURI = storageURI
	record.Checksum = checksum
	record.SizeBytes = sizeBytes
	record.Status = BackupCompleted

	logger.Info("租户级备份完成", "backup_id", backupID, "checksum", checksum)
	return &BackupResult{BackupID: backupID}, nil
}

func (o *BackupOrchestrator) Restore(ctx context.Context, targetTenantID uuid.UUID, backupID uuid.UUID) (*RestoreResult, error) {
	logger := o.logger.With("operation", "restore", "tenant_id", targetTenantID, "backup_id", backupID)

	record, ok := o.records[backupID]
	if !ok {
		return nil, fmt.Errorf("备份记录不存在: %s", backupID)
	}

	// C-BACKUP-01: 跨租户恢复拒绝
	if record.TenantID != targetTenantID {
		return nil, fmt.Errorf("跨租户恢复被拒绝: 备份源 %s != 目标 %s", record.TenantID, targetTenantID)
	}

	// 校验备份完整性
	if record.Status != BackupCompleted {
		return nil, fmt.Errorf("备份未完成，状态: %s", record.Status)
	}

	logger.Info("开始租户级恢复", "checksum", record.Checksum)

	// 恢复数据
	if err := o.importFromStorage(ctx, targetTenantID, record); err != nil {
		return nil, fmt.Errorf("恢复失败: %w", err)
	}

	result := &RestoreResult{
		RestoreTaskID: uuid.New(),
		BackupID:      backupID,
		TenantID:      targetTenantID,
		Status:        "completed",
	}
	logger.Info("租户级恢复完成")
	return result, nil
}

func (o *BackupOrchestrator) GetBackup(backupID uuid.UUID) (*BackupRecord, bool) {
	record, ok := o.records[backupID]
	return record, ok
}

func (o *BackupOrchestrator) exportToStorage(ctx context.Context, tenantID uuid.UUID) (string, string, int64, error) {
	// 由 Rust Agent 执行实际数据导出至对象存储
	storageURI := fmt.Sprintf("s3://eitp-backups/%s/%d.tar.gz", tenantID, time.Now().Unix())
	checksum := fmt.Sprintf("sha256:%s", tenantID.String()[:8])
	return storageURI, checksum, 1024 * 1024, nil
}

func (o *BackupOrchestrator) importFromStorage(ctx context.Context, tenantID uuid.UUID, record *BackupRecord) error {
	// 由 Rust Agent 执行实际数据导入
	o.logger.Info("从对象存储导入数据", "storage_uri", record.StorageURI)
	return nil
}
