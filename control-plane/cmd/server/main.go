package main

import (
	"context"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/eitp/control-plane/api"
	"github.com/eitp/control-plane/internal/auth"
	"github.com/eitp/control-plane/internal/config"
	"github.com/eitp/control-plane/internal/orchestrator"
	"github.com/eitp/control-plane/internal/store"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stderr, &slog.HandlerOptions{Level: slog.LevelInfo}))
	slog.SetDefault(logger)

	cfg := config.Load()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	db, err := store.NewDB(ctx, cfg.PostgresURL)
	if err != nil {
		logger.Warn("数据库连接失败，以降级模式启动", "error", err)
		db = nil
	}
	if db != nil {
		defer db.Close()
	}

	var tenantStore *store.TenantStateStore
	if db != nil {
		tenantStore = store.NewTenantStateStore(db)
	}

	provisioningOrch := orchestrator.NewProvisioningOrchestrator(tenantStore, logger)
	migrationOrch := orchestrator.NewMigrationOrchestrator(tenantStore, logger)
	backupOrch := orchestrator.NewBackupOrchestrator(logger)
	placementMgr := orchestrator.NewPlacementManager(tenantStore, logger)

	handler := api.NewHandler(provisioningOrch, migrationOrch, backupOrch, placementMgr, logger)

	tokenValidator := auth.NewTokenValidator(cfg.PlatformTokenKey)

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", handler.Health)
	mux.HandleFunc("POST /api/v1/platform/tenants", handler.ProvisionTenant)
	mux.HandleFunc("POST /api/v1/platform/tenants/{tenantId}/migrate", handler.MigrateTenant)
	mux.HandleFunc("POST /api/v1/platform/tenants/{tenantId}/backup", handler.BackupTenant)

	server := &http.Server{
		Addr:    ":" + cfg.Port,
		Handler: tokenValidator.Middleware(mux),
	}

	go func() {
		logger.Info("控制面服务启动", "port", cfg.Port)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Error("服务器异常退出", "error", err)
			os.Exit(1)
		}
	}()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	<-sigCh

	logger.Info("正在关闭控制面服务...")
	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownCancel()
	server.Shutdown(shutdownCtx)
	logger.Info("控制面服务已关闭")
}
