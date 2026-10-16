// 外部HTTPの入力検証・応答形式・業務エラーのHTTP変換を担当する。
// 各ハンドラーで共通の検証とエラー応答をここに集約し、同じ失敗を同じステータス・文言で返す。
package presentation

import (
	"bytes"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"mime"
	"net/http"
	"slices"
	"strings"
)

// JavaScriptの整数で安全に扱える更新版の上限。
const maxSafeRevision = 9007199254740990

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("Cache-Control", "no-store")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func writeError(w http.ResponseWriter, status int, detail string) {
	writeJSON(w, status, map[string]string{"detail": detail})
}

// allowMethodは許可したメソッド以外を405で拒否する。
func allowMethod(w http.ResponseWriter, r *http.Request, methods ...string) bool {
	if slices.Contains(methods, r.Method) {
		return true
	}
	w.Header().Set("Allow", strings.Join(methods, ", "))
	writeError(w, 405, "HTTPメソッドが不正です。")
	return false
}

// requireSessionは本人を決めるセッション原値をCookieから取り出す。本人IDは外部入力から受け取らない。
func requireSession(w http.ResponseWriter, r *http.Request) (string, bool) {
	cookie, err := r.Cookie(sessionCookie)
	if err != nil || len(cookie.Value) != 43 {
		writeError(w, 401, "ログインしてください。")
		return "", false
	}
	return cookie.Value, true
}

// rejectQueryはクエリを受け付けないAPIで、指定された場合に422を返す。
func rejectQuery(w http.ResponseWriter, r *http.Request) bool {
	if r.URL.RawQuery == "" {
		return false
	}
	writeError(w, 422, "クエリパラメーターは指定できません。")
	return true
}

// writeTokenは本人データの更新要求のOriginとCSRFトークンを確認し、トークンを返す。
func writeToken(w http.ResponseWriter, r *http.Request, origin string) (string, bool) {
	csrf := r.Header.Get("X-CSRF-Token")
	if r.Header.Get("Origin") != origin || len(csrf) != 64 {
		writeError(w, 403, "操作を確認できません。画面を再読み込みしてください。")
		return "", false
	}
	return csrf, true
}

// readJSONBodyはJSON更新の本文を上限付きで読む。Content-Type不正は415、上限超過は413。
func readJSONBody(w http.ResponseWriter, r *http.Request, limit int64, tooLarge string) ([]byte, bool) {
	media, _, err := mime.ParseMediaType(r.Header.Get("Content-Type"))
	if err != nil || media != "application/json" {
		writeError(w, 415, "JSON形式で送信してください。")
		return nil, false
	}
	body, err := io.ReadAll(http.MaxBytesReader(w, r.Body, limit))
	if err != nil {
		writeError(w, 413, tooLarge)
		return nil, false
	}
	return body, true
}

// writeSharedErrorは成績・所属・科目で共通の業務エラーコードを同じHTTP応答に変換する。
// subjectは利用不可時の文言に使う対象名。変換しなかった場合はfalseを返す。
func writeSharedError(w http.ResponseWriter, code, subject string) bool {
	switch {
	case code == "invalid_credentials" || code == "invalid_csrf":
		writeAuthError(w, code)
	case code == "student_not_found" || code == "profile_not_found":
		writeError(w, 401, "ログインしてください。")
	case code == "revision_conflict":
		writeError(w, 409, "別の画面でデータが更新されました。再取得してから保存してください。")
	case strings.HasSuffix(code, "_unavailable"):
		writeError(w, 503, subject+"を処理できません。時間をおいて再試行してください。")
	default:
		return false
	}
	return true
}

// 従来のPythonのUUIDコンストラクターが受け付けていた表記を標準形へ揃える。
func normalizeUUID(value string) (string, error) {
	value = strings.ReplaceAll(strings.ReplaceAll(value, "urn:", ""), "uuid:", "")
	value = strings.ReplaceAll(strings.Trim(value, "{}"), "-", "")
	if len(value) != 32 {
		return "", errors.New("invalid UUID")
	}
	if _, err := hex.DecodeString(value); err != nil {
		return "", err
	}
	value = strings.ToLower(value)
	return value[:8] + "-" + value[8:12] + "-" + value[12:16] + "-" + value[16:20] + "-" + value[20:], nil
}

// strictObjectは重複キー・未知キー・不足キーを拒否し、各値をそのまま返す。
func strictObject(data []byte, keys ...string) (map[string]json.RawMessage, bool) {
	decoder := json.NewDecoder(bytes.NewReader(data))
	if token, err := decoder.Token(); err != nil || token != json.Delim('{') {
		return nil, false
	}
	allowed := map[string]bool{}
	for _, key := range keys {
		allowed[key] = true
	}
	fields := map[string]json.RawMessage{}
	for decoder.More() {
		token, err := decoder.Token()
		key, ok := token.(string)
		if err != nil || !ok || !allowed[key] || fields[key] != nil {
			return nil, false
		}
		var value json.RawMessage
		if decoder.Decode(&value) != nil {
			return nil, false
		}
		fields[key] = value
	}
	if token, err := decoder.Token(); err != nil || token != json.Delim('}') || len(fields) != len(keys) {
		return nil, false
	}
	if _, err := decoder.Token(); err != io.EOF {
		return nil, false
	}
	return fields, true
}

func isNull(raw json.RawMessage) bool { return string(raw) == "null" }

func decodeString(raw json.RawMessage) (string, bool) {
	var value string
	return value, !isNull(raw) && json.Unmarshal(raw, &value) == nil
}

func decodeInt(raw json.RawMessage, minimum, maximum int64) (int64, bool) {
	var value int64
	return value, !isNull(raw) && json.Unmarshal(raw, &value) == nil && value >= minimum && value <= maximum
}

func decodeUUID(raw json.RawMessage) (string, bool) {
	value, ok := decodeString(raw)
	if !ok {
		return "", false
	}
	id, err := normalizeUUID(value)
	return id, err == nil
}
