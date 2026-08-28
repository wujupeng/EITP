package orchestrator

import (
	"testing"

	"log/slog"

	"github.com/google/uuid"
)

func TestBackupOrchestrator_BackupAndRestore(t *testing.T) {
	logger := slog.Default()
	orch := NewBackupOrchestrator(logger)

	tenantID := uuid.New()
	result, err := orch.Backup(t.Context(), BackupRequest{TenantID: tenantID})
	if err != nil {
		t.Fatalf("backup failed: %v", err)
	}

	record, ok := orch.GetBackup(result.BackupID)
	if !ok {
		t.Fatal("backup record not found")
	}
	if record.Status != BackupCompleted {
		t.Fatalf("expected completed, got %s", record.Status)
	}

	restoreResult, err := orch.Restore(t.Context(), tenantID, result.BackupID)
	if err != nil {
		t.Fatalf("restore failed: %v", err)
	}
	if restoreResult.TenantID != tenantID {
		t.Fatal("tenant ID mismatch in restore")
	}
}

func TestBackupOrchestrator_CrossTenantRestoreDenied(t *testing.T) {
	logger := slog.Default()
	orch := NewBackupOrchestrator(logger)

	tenantA := uuid.New()
	tenantB := uuid.New()

	result, _ := orch.Backup(t.Context(), BackupRequest{TenantID: tenantA})

	_, err := orch.Restore(t.Context(), tenantB, result.BackupID)
	if err == nil {
		t.Fatal("expected cross-tenant restore to be denied")
	}
}
