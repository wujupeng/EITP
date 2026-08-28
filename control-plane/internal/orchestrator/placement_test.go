package orchestrator

import (
	"testing"

	"log/slog"

	"github.com/eitp/control-plane/internal/store"
	"github.com/google/uuid"
)

func TestPlacementManager_SetAndGetConnectionTarget(t *testing.T) {
	logger := slog.Default()
	mgr := NewPlacementManager(nil, logger)

	tenantID := uuid.New()
	target, err := mgr.GetConnectionTarget(t.Context(), tenantID)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if target != "shared-db-default" {
		t.Fatalf("expected shared-db-default, got %s", target)
	}

	record, err := mgr.SetPlacement(t.Context(), tenantID, store.PlacementDedicatedDB)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if record.Placement != store.PlacementDedicatedDB {
		t.Fatalf("expected dedicated_db, got %s", record.Placement)
	}

	target, _ = mgr.GetConnectionTarget(t.Context(), tenantID)
	if target == "shared-db-default" {
		t.Fatal("expected dedicated connection target after SetPlacement")
	}
}

func TestPlacementManager_MigrationSuggestion_BelowThreshold(t *testing.T) {
	logger := slog.Default()
	mgr := NewPlacementManager(nil, logger)

	metrics := TenantScaleMetrics{
		TenantID:       uuid.New(),
		OrderCount:     1000,
		WarehouseCount: 5,
		SkuCount:       500,
		UserCount:      50,
	}
	suggestion := mgr.EvaluateMigrationSuggestion(metrics)
	if suggestion != nil {
		t.Fatal("expected nil suggestion below threshold")
	}
}

func TestPlacementManager_MigrationSuggestion_ExceedsOrderThreshold(t *testing.T) {
	logger := slog.Default()
	mgr := NewPlacementManager(nil, logger)

	metrics := TenantScaleMetrics{
		TenantID:   uuid.New(),
		OrderCount: 6_000_000,
	}
	suggestion := mgr.EvaluateMigrationSuggestion(metrics)
	if suggestion == nil {
		t.Fatal("expected suggestion above threshold")
	}
	if suggestion.SuggestedPlacement != store.PlacementDedicatedDB {
		t.Fatalf("expected dedicated_db, got %s", suggestion.SuggestedPlacement)
	}
}

func TestPlacementManager_MigrationSuggestion_HugeTenantDedicatedInstance(t *testing.T) {
	logger := slog.Default()
	mgr := NewPlacementManager(nil, logger)

	metrics := TenantScaleMetrics{
		TenantID:   uuid.New(),
		OrderCount: 15_000_000,
	}
	suggestion := mgr.EvaluateMigrationSuggestion(metrics)
	if suggestion == nil {
		t.Fatal("expected suggestion above threshold")
	}
	if suggestion.SuggestedPlacement != store.PlacementDedicatedInstance {
		t.Fatalf("expected dedicated_instance, got %s", suggestion.SuggestedPlacement)
	}
}

func TestMigrationOrchestrator_IsWriteFrozen(t *testing.T) {
	logger := slog.Default()
	orch := NewMigrationOrchestrator(nil, logger)

	tenantID := uuid.New()
	if orch.IsWriteFrozen(tenantID) {
		t.Fatal("expected not frozen initially")
	}
}
