package controllers

import "grad-checker/backend/apps/api/middleware"

import "grad-checker/backend/apps/api/schemas"

import (
	"errors"
	"net/http"

	"grad-checker/backend/modules/grades/application/ports"
)

// 本人成績の全集合を取得・置換する。回次の業務ルールはPythonで判定する。
func NewGradeHandler(gateway ports.GradeGateway, origin string, fallback http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/me/grades" {
			fallback.ServeHTTP(w, r)
			return
		}
		w.Header().Set("Cache-Control", "no-store")
		if !middleware.AllowMethod(w, r, http.MethodGet, http.MethodPut) {
			return
		}
		token, ok := middleware.RequireSession(w, r)
		if !ok || middleware.RejectQuery(w, r) {
			return
		}
		call := ports.GradeCall{Operation: "get", Token: token}
		if r.Method == http.MethodPut {
			csrf, ok := middleware.WriteToken(w, r, origin)
			if !ok {
				return
			}
			body, ok := middleware.ReadJSONBody(w, r, schemas.MaxGradeBody, "送信する成績の量が上限を超えています。")
			if !ok {
				return
			}
			gradeSet, detail := schemas.DecodeGradeSet(body)
			if gradeSet == nil {
				schemas.WriteError(w, 422, detail)
				return
			}
			call.Operation, call.CSRF, call.GradeSet = "save", csrf, gradeSet
		}
		result, err := gateway.Call(r.Context(), call)
		if err != nil {
			writeGradeError(w, err)
			return
		}
		schemas.WriteJSON(w, 200, result)
	})
}

func writeGradeError(w http.ResponseWriter, err error) {
	var business *ports.GradeError
	if !errors.As(err, &business) {
		schemas.WriteError(w, 502, "成績サービスに接続できません。時間をおいて再試行してください。")
		return
	}
	if writeSharedError(w, business.Code, "成績") {
		return
	}
	switch business.Code {
	case "unknown_course":
		schemas.WriteError(w, 400, "選択した科目が見つかりません。科目一覧を再読み込みしてください。")
	case "duplicate_attempt":
		schemas.WriteError(w, 422, "同じ科目の履修回次が重複しています。")
	case "invalid_attempt_sequence":
		schemas.WriteError(w, 422, "履修回次は1から順に入力してください。再履修は不合格（D・X）の後だけ追加できます。")
	default:
		schemas.WriteError(w, 502, "成績サービスの応答を読み込めません。")
	}
}
