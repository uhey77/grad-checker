package tests

import (
	"grad-checker/backend/apps/api/controllers"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestReadinessRequiresPythonAndDatabase(t *testing.T) {
	for _, healthy := range []bool{true, false} {
		upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if r.URL.Path != "/bridge/health" {
				t.Error("unexpected probe path")
			}
			if !healthy {
				w.WriteHeader(503)
			}
			if healthy {
				w.Write([]byte(`{"status":"ok"}`))
			} else {
				w.Write([]byte(`{"status":"unavailable"}`))
			}
		}))
		handler := controllers.NewReadinessHandler(upstream.URL, http.NotFoundHandler())
		result := httptest.NewRecorder()
		handler.ServeHTTP(result, httptest.NewRequest("GET", "/api/ready", nil))
		expected := 503
		if healthy {
			expected = 200
		}
		if result.Code != expected {
			t.Fatalf("status=%d", result.Code)
		}
		if result.Header().Get("Cache-Control") != "no-store" {
			t.Fatal("probe was cacheable")
		}
		upstream.Close()
		result = httptest.NewRecorder()
		handler.ServeHTTP(result, httptest.NewRequest("GET", "/api/ready", nil))
		if result.Code != 503 {
			t.Fatal("failed Python service must not be ready")
		}
	}
}
