package auth

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"net/http"
	"strings"
)

type TokenValidator struct {
	secretKey string
}

func NewTokenValidator(secretKey string) *TokenValidator {
	return &TokenValidator{secretKey: secretKey}
}

func (v *TokenValidator) Validate(r *http.Request) bool {
	token := r.Header.Get("X-Platform-Token")
	if token == "" {
		return false
	}
	return v.validateToken(token)
}

func (v *TokenValidator) validateToken(token string) bool {
	parts := strings.SplitN(token, ".", 2)
	if len(parts) != 2 {
		return false
	}
	payload := parts[0]
	signature := parts[1]

	mac := hmac.New(sha256.New, []byte(v.secretKey))
	mac.Write([]byte(payload))
	expectedSig := hex.EncodeToString(mac.Sum(nil))

	return hmac.Equal([]byte(signature), []byte(expectedSig))
}

func (v *TokenValidator) Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/health" {
			next.ServeHTTP(w, r)
			return
		}
		if !v.Validate(r) {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusUnauthorized)
			w.Write([]byte(`{"error_code":"EITP_MT_PLATFORM_TOKEN_INVALID","message":"平台令牌非法或缺失"}`))
			return
		}
		next.ServeHTTP(w, r)
	})
}
