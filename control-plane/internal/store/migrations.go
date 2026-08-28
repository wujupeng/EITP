package store

import (
	"context"
	"fmt"
	"log/slog"
)

type Migration struct {
	Version     string
	Description string
	UpSQL       string
	DownSQL     string
}

type MigrationRunner struct {
	db     *DB
	logger *slog.Logger
}

func NewMigrationRunner(db *DB, logger *slog.Logger) *MigrationRunner {
	return &MigrationRunner{db: db, logger: logger}
}

func (r *MigrationRunner) Run(ctx context.Context) error {
	if r.db == nil {
		return fmt.Errorf("数据库连接不可用")
	}

	if err := r.ensureMigrationTable(ctx); err != nil {
		return fmt.Errorf("创建迁移跟踪表失败: %w", err)
	}

	migrations := getMigrations()
	for _, m := range migrations {
		applied, err := r.isApplied(ctx, m.Version)
		if err != nil {
			return err
		}
		if applied {
			r.logger.Debug("迁移已应用，跳过", "version", m.Version)
			continue
		}

		r.logger.Info("执行迁移", "version", m.Version, "description", m.Description)
		if _, err := r.db.Pool.Exec(ctx, m.UpSQL); err != nil {
			return fmt.Errorf("迁移 %s 失败: %w", m.Version, err)
		}
		if err := r.recordMigration(ctx, m.Version); err != nil {
			return err
		}
		r.logger.Info("迁移完成", "version", m.Version)
	}

	return nil
}

func (r *MigrationRunner) ensureMigrationTable(ctx context.Context) error {
	_, err := r.db.Pool.Exec(ctx, `
		CREATE TABLE IF NOT EXISTS schema_migrations (
			version VARCHAR(255) PRIMARY KEY,
			applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
		)
	`)
	return err
}

func (r *MigrationRunner) isApplied(ctx context.Context, version string) (bool, error) {
	var exists bool
	err := r.db.Pool.QueryRow(ctx,
		`SELECT EXISTS(SELECT 1 FROM schema_migrations WHERE version = $1)`, version).Scan(&exists)
	return exists, err
}

func (r *MigrationRunner) recordMigration(ctx context.Context, version string) error {
	_, err := r.db.Pool.Exec(ctx,
		`INSERT INTO schema_migrations (version) VALUES ($1) ON CONFLICT DO NOTHING`, version)
	return err
}

func getMigrations() []Migration {
	return []Migration{
		{
			Version:     "001",
			Description: "创建租户状态表",
			UpSQL:       migration001Up,
			DownSQL:     migration001Down,
		},
	}
}

const migration001Up = `
CREATE TABLE IF NOT EXISTS tenant_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enterprise_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'provisioning',
    data_placement VARCHAR(50) NOT NULL DEFAULT 'shared_db',
    version INTEGER NOT NULL DEFAULT 1,
    idempotency_key VARCHAR(255) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tenant_state_status ON tenant_state(status);
CREATE INDEX IF NOT EXISTS idx_tenant_state_idempotency ON tenant_state(idempotency_key);
`

const migration001Down = `
DROP TABLE IF EXISTS tenant_state;
`
