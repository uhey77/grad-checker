package controllers

import (
	"encoding/json"
	"net/http"
	"time"

	"grad-checker/backend/apps/api/middleware"
	"grad-checker/backend/apps/api/schemas"
)

// NewReadinessHandlerはGo→Python→DBの接続を確認する。livenessとは分離する。
func NewReadinessHandler(pythonURL string, next http.Handler) http.Handler {
	client := &http.Client{Timeout: 3 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/ready" {
			next.ServeHTTP(w, r)
			return
		}
		if !middleware.AllowMethod(w, r, http.MethodGet) {
			return
		}
		request, err := http.NewRequestWithContext(r.Context(), http.MethodGet, pythonURL+"/bridge/health", nil)
		if err != nil {
			schemas.WriteJSON(w, 503, map[string]string{"status": "unavailable"})
			return
		}
		response, err := client.Do(request)
		if err != nil {
			schemas.WriteJSON(w, 503, map[string]string{"status": "unavailable"})
			return
		}
		defer response.Body.Close()
		var result struct {
			Status string `json:"status"`
		}
		if response.StatusCode != 200 || json.NewDecoder(http.MaxBytesReader(w, response.Body, 1024)).Decode(&result) != nil || result.Status != "ok" {
			schemas.WriteJSON(w, 503, map[string]string{"status": "unavailable"})
			return
		}
		schemas.WriteJSON(w, 200, map[string]string{"status": "ok"})
	})
}
