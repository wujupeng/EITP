package api

import (
	"encoding/json"
	"log/slog"
	"net/http"

	"github.com/eitp/control-plane/internal/orchestrator"
	"github.com/eitp/control-plane/internal/store"
	"github.com/google/uuid"
)

type Handler struct {
	provisioning *orchestrator.ProvisioningOrchestrator
	migration    *orchestrator.MigrationOrchestrator
	backup       *orchestrator.BackupOrchestrator
	placement    *orchestrator.PlacementManager
	logger       *slog.Logger
}

func NewHandler(
	p *orchestrator.ProvisioningOrchestrator,
	m *orchestrator.MigrationOrchestrator,
	b *orchestrator.BackupOrchestrator,
	pm *orchestrator.PlacementManager,
	logger *slog.Logger,
) *Handler {
	return &Handler{
		provisioning: p,
		migration:    m,
		backup:       b,
		placement:    pm,
		logger:       logger,
	}
}

func (h *Handler) Health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (h *Handler) ProvisionTenant(w http.ResponseWriter, r *http.Request) {
	var req orchestrator.ProvisionRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "EITP_MT_INVALID_REQUEST", "请求体解析失败")
		return
	}

	result, err := h.provisioning.Provision(r.Context(), req)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "EITP_MT_PROVISION_FAILED", err.Error())
		return
	}

	writeJSON(w, http.StatusCreated, map[string]any{
		"tenant_id": result.TenantID,
		"duration":  result.Duration.String(),
	})
}

func (h *Handler) MigrateTenant(w http.ResponseWriter, r *http.Request) {
	tenantIDStr := r.PathValue("tenantId")
	tenantID, err := uuid.Parse(tenantIDStr)
	if err != nil {
		writeError(w, http.StatusBadRequest, "EITP_MT_INVALID_REQUEST", "租户 ID 格式错误")
		return
	}

	var body struct {
		TargetPlacement string `json:"target_placement"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeError(w, http.StatusBadRequest, "EITP_MT_INVALID_REQUEST", "请求体解析失败")
		return
	}

	req := orchestrator.MigrationRequest{
		TenantID:        tenantID,
		TargetPlacement: parsePlacement(body.TargetPlacement),
	}

	if _, err := h.migration.Migrate(r.Context(), req); err != nil {
		writeError(w, http.StatusInternalServerError, "EITP_MT_MIGRATION_IN_PROGRESS", err.Error())
		return
	}

	writeJSON(w, http.StatusAccepted, map[string]string{"status": "migrated"})
}

func (h *Handler) BackupTenant(w http.ResponseWriter, r *http.Request) {
	tenantIDStr := r.PathValue("tenantId")
	tenantID, err := uuid.Parse(tenantIDStr)
	if err != nil {
		writeError(w, http.StatusBadRequest, "EITP_MT_INVALID_REQUEST", "租户 ID 格式错误")
		return
	}

	result, err := h.backup.Backup(r.Context(), orchestrator.BackupRequest{TenantID: tenantID})
	if err != nil {
		writeError(w, http.StatusInternalServerError, "EITP_MT_BACKUP_FAILED", err.Error())
		return
	}

	writeJSON(w, http.StatusCreated, map[string]any{"backup_id": result.BackupID})
}

func writeJSON(w http.ResponseWriter, status int, data any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}

func writeError(w http.ResponseWriter, status int, code, message string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(map[string]string{"error_code": code, "message": message})
}

func parsePlacement(s string) store.DataPlacement {
	return store.DataPlacement(s)
}
