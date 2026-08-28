package config

import (
	"os"
	"strconv"
)

type Config struct {
	Port             string
	PostgresURL      string
	IAMBaseURL       string
	BillingBaseURL   string
	AppBaseURL       string
	PlatformTokenKey string
	TaskQueueWorkers int
}

func Load() *Config {
	return &Config{
		Port:             getEnv("EITP_CP_PORT", "8090"),
		PostgresURL:      getEnv("EITP_CP_DATABASE_URL", "postgres://eitp:eitp@localhost:5432/eitp_control"),
		IAMBaseURL:       getEnv("EITP_IAM_BASE_URL", "http://localhost:8081"),
		BillingBaseURL:   getEnv("EITP_BILLING_BASE_URL", "http://localhost:8082"),
		AppBaseURL:       getEnv("EITP_APP_BASE_URL", "http://localhost:8000"),
		PlatformTokenKey: getEnv("EITP_PLATFORM_TOKEN_KEY", "change-me-in-production"),
		TaskQueueWorkers: getEnvInt("EITP_CP_QUEUE_WORKERS", 4),
	}
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func getEnvInt(key string, fallback int) int {
	if v := os.Getenv(key); v != "" {
		if i, err := strconv.Atoi(v); err == nil {
			return i
		}
	}
	return fallback
}
