package orchestrator

import (
	"context"
	"fmt"
	"log/slog"

	"github.com/eitp/control-plane/internal/store"
	"github.com/google/uuid"
)

type PlacementManager struct {
	tenantStore *store.TenantStateStore
	logger      *slog.Logger
	records     map[uuid.UUID]*PlacementRecord
}

type PlacementRecord struct {
	TenantID         uuid.UUID
	Placement        store.DataPlacement
	ConnectionTarget string
}

type PlacementDecision struct {
	TenantID  uuid.UUID
	Placement store.DataPlacement
	Reason    string
}

type TenantScaleMetrics struct {
	TenantID       uuid.UUID
	OrderCount     int64
	WarehouseCount int64
	SkuCount       int64
	UserCount      int64
}

const (
	orderThreshold     = 5_000_000
	warehouseThreshold = 100
	skuThreshold       = 100_000
	userThreshold      = 3_000
)

func NewPlacementManager(ts *store.TenantStateStore, logger *slog.Logger) *PlacementManager {
	return &PlacementManager{
		tenantStore: ts,
		logger:      logger,
		records:     make(map[uuid.UUID]*PlacementRecord),
	}
}

func (m *PlacementManager) EvaluatePlacement(ctx context.Context, tenantID uuid.UUID) (*PlacementDecision, error) {
	logger := m.logger.With("operation", "evaluate_placement", "tenant_id", tenantID)

	decision := &PlacementDecision{
		TenantID:  tenantID,
		Placement: store.PlacementSharedDB,
		Reason:    "默认共享数据库放置",
	}
	logger.Info("放置策略评估完成", "placement", decision.Placement)
	return decision, nil
}

func (m *PlacementManager) GetConnectionTarget(ctx context.Context, tenantID uuid.UUID) (string, error) {
	if record, ok := m.records[tenantID]; ok {
		return record.ConnectionTarget, nil
	}
	return "shared-db-default", nil
}

func (m *PlacementManager) SetPlacement(ctx context.Context, tenantID uuid.UUID, placement store.DataPlacement) (*PlacementRecord, error) {
	target := m.defaultTarget(placement, tenantID)
	record := &PlacementRecord{
		TenantID:         tenantID,
		Placement:        placement,
		ConnectionTarget: target,
	}
	m.records[tenantID] = record
	m.logger.Info("放置模式设置", "tenant_id", tenantID, "placement", placement)
	return record, nil
}

func (m *PlacementManager) defaultTarget(placement store.DataPlacement, tenantID uuid.UUID) string {
	switch placement {
	case store.PlacementSharedDB:
		return "shared-db-default"
	case store.PlacementDedicatedDB:
		return fmt.Sprintf("dedicated-db-%s", tenantID)
	case store.PlacementDedicatedInstance:
		return fmt.Sprintf("dedicated-instance-%s", tenantID)
	default:
		return "shared-db-default"
	}
}

type MigrationSuggestion struct {
	TenantID           uuid.UUID
	SuggestedPlacement store.DataPlacement
	Reason             string
	ExceededMetrics    map[string]interface{}
}

func (m *PlacementManager) EvaluateMigrationSuggestion(metrics TenantScaleMetrics) *MigrationSuggestion {
	exceeded := make(map[string]interface{})

	if metrics.OrderCount >= orderThreshold {
		exceeded["order_count"] = map[string]int64{"current": metrics.OrderCount, "threshold": orderThreshold}
	}
	if metrics.WarehouseCount >= warehouseThreshold {
		exceeded["warehouse_count"] = map[string]int64{"current": metrics.WarehouseCount, "threshold": warehouseThreshold}
	}
	if metrics.SkuCount >= skuThreshold {
		exceeded["sku_count"] = map[string]int64{"current": metrics.SkuCount, "threshold": skuThreshold}
	}
	if metrics.UserCount >= userThreshold {
		exceeded["user_count"] = map[string]int64{"current": metrics.UserCount, "threshold": userThreshold}
	}

	if len(exceeded) == 0 {
		return nil
	}

	suggested := store.PlacementDedicatedDB
	if metrics.OrderCount >= 10_000_000 {
		suggested = store.PlacementDedicatedInstance
	}

	return &MigrationSuggestion{
		TenantID:           metrics.TenantID,
		SuggestedPlacement: suggested,
		Reason:             "租户规模超过大客户阈值，建议迁移至独立放置",
		ExceededMetrics:    exceeded,
	}
}
