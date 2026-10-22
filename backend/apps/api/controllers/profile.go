package controllers

import "grad-checker/backend/apps/api/middleware"

import "grad-checker/backend/apps/api/schemas"

import (
	"errors"
	"net/http"

	"grad-checker/backend/modules/accounts/application/ports"
)

// 本人IDを外部入力から受け取らず、セッション原値をPythonサービスで検証する。
func NewProfileHandler(gateway ports.ProfileGateway, origin string, fallback http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		operation, method := "", http.MethodGet
		switch r.URL.Path {
		case "/api/programs":
			operation = "programs"
		case "/api/me":
			operation = "me"
		case "/api/me/program":
			operation, method = "save_program", http.MethodPut
		default:
			fallback.ServeHTTP(w, r)
			return
		}
		w.Header().Set("Cache-Control", "no-store")
		if !middleware.AllowMethod(w, r, method) {
			return
		}
		token, ok := middleware.RequireSession(w, r)
		if !ok || middleware.RejectQuery(w, r) {
			return
		}
		call := ports.ProfileCall{Operation: operation, Token: token}
		if operation == "save_program" {
			csrf, ok := middleware.WriteToken(w, r, origin)
			if !ok {
				return
			}
			body, ok := middleware.ReadJSONBody(w, r, 4096, schemas.SelectionDetail)
			if !ok {
				return
			}
			selection, ok := schemas.DecodeSelection(body)
			if !ok {
				schemas.WriteError(w, 422, schemas.SelectionDetail)
				return
			}
			call.CSRF, call.Selection = csrf, selection
		}
		result, err := gateway.Call(r.Context(), call)
		if err != nil {
			writeProfileError(w, err)
			return
		}
		if operation == "programs" {
			schemas.WriteJSON(w, 200, result)
		} else {
			schemas.WriteJSON(w, 200, result.Profile)
		}
	})
}

func writeProfileError(w http.ResponseWriter, err error) {
	var business *ports.AuthError
	if !errors.As(err, &business) {
		schemas.WriteError(w, 502, "所属サービスに接続できません。時間をおいて再試行してください。")
		return
	}
	if writeSharedError(w, business.Code, "所属情報") {
		return
	}
	if business.Code == "invalid_program" {
		schemas.WriteError(w, 422, "所属とカリキュラムの組合せが不正です。選択肢を再取得してください。")
		return
	}
	schemas.WriteError(w, 502, "所属サービスの応答を読み込めません。")
}
