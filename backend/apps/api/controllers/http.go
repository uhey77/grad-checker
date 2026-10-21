package controllers

import "grad-checker/backend/apps/api/schemas"

import (
	"net/http"

	"strings"
)

// writeSharedErrorは成績・所属・科目で共通の業務エラーコードを同じHTTP応答に変換する。
// subjectは利用不可時の文言に使う対象名。変換しなかった場合はfalseを返す。
func writeSharedError(w http.ResponseWriter, code, subject string) bool {
	switch {
	case code == "invalid_credentials" || code == "invalid_csrf":
		writeAuthError(w, code)
	case code == "student_not_found" || code == "profile_not_found":
		schemas.WriteError(w, 401, "ログインしてください。")
	case code == "revision_conflict":
		schemas.WriteError(w, 409, "別の画面でデータが更新されました。再取得してから保存してください。")
	case strings.HasSuffix(code, "_unavailable"):
		schemas.WriteError(w, 503, subject+"を処理できません。時間をおいて再試行してください。")
	default:
		return false
	}
	return true
}
