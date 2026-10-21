package controllers

import "grad-checker/backend/apps/api/middleware"

import (
	"embed"
	"net/http"
)

//go:embed apidocs/openapi.json apidocs/index.html
var apiDocs embed.FS

// NewAPIDocsHandlerは明示的に有効化した開発環境だけでGo公開仕様を配信する。
func NewAPIDocsHandler(enabled bool, fallback http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !enabled || (r.URL.Path != "/docs" && r.URL.Path != "/openapi.json") {
			fallback.ServeHTTP(w, r)
			return
		}
		if !middleware.AllowMethod(w, r, http.MethodGet) {
			return
		}
		w.Header().Set("Cache-Control", "no-store")
		w.Header().Set("Referrer-Policy", "no-referrer")
		w.Header().Set("X-Content-Type-Options", "nosniff")
		path, media := "apidocs/openapi.json", "application/json; charset=utf-8"
		if r.URL.Path == "/docs" {
			path, media = "apidocs/index.html", "text/html; charset=utf-8"
		}
		body, _ := apiDocs.ReadFile(path) // go:embedで存在をコンパイル時に検証する。
		w.Header().Set("Content-Type", media)
		_, _ = w.Write(body)
	})
}
