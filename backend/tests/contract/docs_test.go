package tests

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"grad-checker/backend/apps/api/controllers"
)

func TestAPIDocsServing(t *testing.T) {
	fallback := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	})
	for _, enabled := range []bool{false, true} {
		handler := controllers.NewAPIDocsHandler(enabled, fallback)
		for _, path := range []string{"/docs", "/openapi.json"} {
			w := httptest.NewRecorder()
			handler.ServeHTTP(w, httptest.NewRequest(http.MethodGet, path, nil))
			if !enabled {
				if w.Code != http.StatusNotFound {
					t.Fatalf("disabled %s: %d", path, w.Code)
				}
				continue
			}
			if w.Code != http.StatusOK || w.Header().Get("Cache-Control") != "no-store" {
				t.Fatalf("enabled %s: %d %v", path, w.Code, w.Header())
			}
			if path == "/docs" {
				if !strings.HasPrefix(w.Header().Get("Content-Type"), "text/html") || !strings.Contains(w.Body.String(), "SwaggerUIBundle") {
					t.Fatal("Swagger UI HTML is missing")
				}
			} else {
				var document struct {
					OpenAPI string `json:"openapi"`
				}
				if err := json.Unmarshal(w.Body.Bytes(), &document); err != nil || document.OpenAPI != "3.1.0" {
					t.Fatalf("invalid embedded OpenAPI: %v", err)
				}
			}
			w = httptest.NewRecorder()
			handler.ServeHTTP(w, httptest.NewRequest(http.MethodPost, path, nil))
			if w.Code != http.StatusMethodNotAllowed || w.Header().Get("Allow") != "GET" {
				t.Fatalf("POST %s: %d", path, w.Code)
			}
		}
		w := httptest.NewRecorder()
		handler.ServeHTTP(w, httptest.NewRequest(http.MethodGet, "/unrelated", nil))
		if w.Code != http.StatusNotFound {
			t.Fatalf("fallback: %d", w.Code)
		}
	}
}
