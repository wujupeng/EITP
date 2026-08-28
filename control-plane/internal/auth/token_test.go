package auth

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"net/http"
	"net/http/httptest"
	"testing"
)

func generateValidToken(secret, payload string) string {
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(payload))
	sig := hex.EncodeToString(mac.Sum(nil))
	return payload + "." + sig
}

func TestTokenValidator_ValidToken(t *testing.T) {
	validator := NewTokenValidator("test-secret")
	token := generateValidToken("test-secret", "test-payload")

	req := httptest.NewRequest("POST", "/api/v1/platform/tenants", nil)
	req.Header.Set("X-Platform-Token", token)

	if !validator.Validate(req) {
		t.Error("有效令牌应通过校验")
	}
}

func TestTokenValidator_MissingToken(t *testing.T) {
	validator := NewTokenValidator("test-secret")

	req := httptest.NewRequest("POST", "/api/v1/platform/tenants", nil)

	if validator.Validate(req) {
		t.Error("缺失令牌应被拒绝")
	}
}

func TestTokenValidator_InvalidToken(t *testing.T) {
	validator := NewTokenValidator("test-secret")

	req := httptest.NewRequest("POST", "/api/v1/platform/tenants", nil)
	req.Header.Set("X-Platform-Token", "invalid-token")

	if validator.Validate(req) {
		t.Error("非法令牌应被拒绝")
	}
}

func TestTokenValidator_Middleware_RejectsInvalid(t *testing.T) {
	validator := NewTokenValidator("test-secret")

	handler := validator.Middleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	req := httptest.NewRequest("POST", "/api/v1/platform/tenants", nil)
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	if rr.Code != http.StatusUnauthorized {
		t.Errorf("非法令牌应返回 401，实际返回 %d", rr.Code)
	}
}

func TestTokenValidator_Middleware_SkipsHealth(t *testing.T) {
	validator := NewTokenValidator("test-secret")

	handler := validator.Middleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	req := httptest.NewRequest("GET", "/health", nil)
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	if rr.Code != http.StatusOK {
		t.Errorf("健康检查应跳过令牌校验返回 200，实际返回 %d", rr.Code)
	}
}
