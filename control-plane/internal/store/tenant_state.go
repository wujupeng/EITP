package store

import (
	"context"
	"time"

	"github.com/google/uuid"
)

type TenantStatus string

const (
	StatusProvisioning  TenantStatus = "provisioning"
	StatusActive        TenantStatus = "active"
	StatusDisabled      TenantStatus = "disabled"
	StatusDeprovisioned TenantStatus = "deprovisioned"
	StatusFailed        TenantStatus = "failed"
)

type DataPlacement string

const (
	PlacementSharedDB          DataPlacement = "shared_db"
	PlacementDedicatedDB       DataPlacement = "dedicated_db"
	PlacementDedicatedInstance DataPlacement = "dedicated_instance"
)

type TenantState struct {
	ID             uuid.UUID
	EnterpriseName string
	Status         TenantStatus
	DataPlacement  DataPlacement
	Version        int
	CreatedAt      time.Time
	UpdatedAt      time.Time
}

type TenantStateStore struct {
	db *DB
}

func NewTenantStateStore(db *DB) *TenantStateStore {
	return &TenantStateStore{db: db}
}

func (s *TenantStateStore) GetByID(ctx context.Context, id uuid.UUID) (*TenantState, error) {
	row := s.db.Pool.QueryRow(ctx,
		`SELECT id, enterprise_name, status, data_placement, version, created_at, updated_at
		 FROM tenant_state WHERE id = $1`, id)

	var ts TenantState
	err := row.Scan(&ts.ID, &ts.EnterpriseName, &ts.Status, &ts.DataPlacement,
		&ts.Version, &ts.CreatedAt, &ts.UpdatedAt)
	if err != nil {
		return nil, err
	}
	return &ts, nil
}

func (s *TenantStateStore) UpdateStatus(ctx context.Context, id uuid.UUID, status TenantStatus) error {
	_, err := s.db.Pool.Exec(ctx,
		`UPDATE tenant_state SET status = $2, updated_at = NOW() WHERE id = $1`,
		id, status)
	return err
}
