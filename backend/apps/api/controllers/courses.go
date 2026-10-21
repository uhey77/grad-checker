package controllers

import "grad-checker/backend/apps/api/middleware"

import "grad-checker/backend/apps/api/schemas"

import (
	"errors"
	"net/http"

	"grad-checker/backend/modules/subjects/application/ports"
)

// 本人課程から見た科目一覧・分類を返す。本人課程は外部入力ではなくセッションから決める。
func NewCourseHandler(reader ports.CourseCatalogReader, fallback http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		operation := ""
		switch r.URL.Path {
		case "/api/courses":
			operation = "courses"
		case "/api/categories":
			operation = "categories"
		default:
			fallback.ServeHTTP(w, r)
			return
		}
		w.Header().Set("Cache-Control", "no-store")
		if !middleware.AllowMethod(w, r, http.MethodGet) {
			return
		}
		token, ok := middleware.RequireSession(w, r)
		if !ok {
			return
		}
		call := ports.CourseCatalogCall{Operation: operation, Token: token}
		if operation == "categories" {
			if middleware.RejectQuery(w, r) {
				return
			}
		} else {
			filters, detail := schemas.ParseCourseFilters(r.URL.RawQuery)
			if filters == nil {
				schemas.WriteError(w, 422, detail)
				return
			}
			call.Filters = filters
		}
		data, err := reader.Call(r.Context(), call)
		if err != nil {
			writeCourseError(w, err)
			return
		}
		schemas.WriteJSON(w, 200, data)
	})
}

func writeCourseError(w http.ResponseWriter, err error) {
	var business *ports.CourseCatalogError
	if errors.As(err, &business) {
		switch business.Code {
		case "invalid_credentials", "profile_not_found":
			writeSharedError(w, business.Code, "科目データ")
		case "program_not_selected":
			schemas.WriteError(w, 409, "所属課程を設定してから科目を表示してください。")
		case "unknown_category":
			schemas.WriteError(w, 422, "指定した科目区分は本人の課程にありません。科目区分を選び直してください。")
		case "curriculum_not_found":
			schemas.WriteError(w, 409, "所属課程のデータが見つかりません。所属を設定し直してください。")
		case "classification_inconsistent":
			schemas.WriteError(w, 409, "科目分類のデータが不整合です。課程・科目データを確認してください。")
		case "catalog_unavailable", "profile_unavailable", "auth_unavailable":
			schemas.WriteError(w, 503, "科目データを読み込めません。時間をおいて再試行してください。")
		default:
			schemas.WriteError(w, 502, "科目サービスの応答を読み込めません。")
		}
		return
	}
	if errors.Is(err, ports.ErrTimeout) {
		schemas.WriteError(w, 504, "Pythonサービスの応答がタイムアウトしました。")
		return
	}
	schemas.WriteError(w, 502, "科目サービスに接続できません。時間をおいて再試行してください。")
}
