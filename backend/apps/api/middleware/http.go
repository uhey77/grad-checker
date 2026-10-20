package middleware

import "grad-checker/backend/apps/api/schemas"

import (
	"io"
	"mime"
	"net/http"
	"slices"
	"strings"
)

// allowMethodは許可したメソッド以外を405で拒否する。
func AllowMethod(w http.ResponseWriter, r *http.Request, methods ...string) bool {
	if slices.Contains(methods, r.Method) {
		return true
	}
	w.Header().Set("Allow", strings.Join(methods, ", "))
	schemas.WriteError(w, 405, "HTTPメソッドが不正です。")
	return false
}

// requireSessionは本人を決めるセッション原値をCookieから取り出す。本人IDは外部入力から受け取らない。
func RequireSession(w http.ResponseWriter, r *http.Request) (string, bool) {
	cookie, err := r.Cookie(SessionCookie)
	if err != nil || len(cookie.Value) != 43 {
		schemas.WriteError(w, 401, "ログインしてください。")
		return "", false
	}
	return cookie.Value, true
}

// rejectQueryはクエリを受け付けないAPIで、指定された場合に422を返す。
func RejectQuery(w http.ResponseWriter, r *http.Request) bool {
	if r.URL.RawQuery == "" {
		return false
	}
	schemas.WriteError(w, 422, "クエリパラメーターは指定できません。")
	return true
}

// writeTokenは本人データの更新要求のOriginとCSRFトークンを確認し、トークンを返す。
func WriteToken(w http.ResponseWriter, r *http.Request, origin string) (string, bool) {
	csrf := r.Header.Get("X-CSRF-Token")
	if r.Header.Get("Origin") != origin || len(csrf) != 64 {
		schemas.WriteError(w, 403, "操作を確認できません。画面を再読み込みしてください。")
		return "", false
	}
	return csrf, true
}

// readJSONBodyはJSON更新の本文を上限付きで読む。Content-Type不正は415、上限超過は413。
func ReadJSONBody(w http.ResponseWriter, r *http.Request, limit int64, tooLarge string) ([]byte, bool) {
	media, _, err := mime.ParseMediaType(r.Header.Get("Content-Type"))
	if err != nil || media != "application/json" {
		schemas.WriteError(w, 415, "JSON形式で送信してください。")
		return nil, false
	}
	body, err := io.ReadAll(http.MaxBytesReader(w, r.Body, limit))
	if err != nil {
		schemas.WriteError(w, 413, tooLarge)
		return nil, false
	}
	return body, true
}
