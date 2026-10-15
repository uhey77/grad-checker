package presentation

import (
	"encoding/json"
	"errors"
	"io"
	"mime"
	"net/http"

	"grad-checker/backend/modules/accounts/application"
)

// 本人IDを外部入力から受け取らず、セッション原値を内部サービスで検証する。
func NewProfileHandler(gateway application.ProfileGateway, origin string, fallback http.Handler) http.Handler {
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
		if r.Method != method {
			w.Header().Set("Allow", method)
			writeError(w, 405, "HTTPメソッドが不正です。")
			return
		}
		cookie, err := r.Cookie(sessionCookie)
		if err != nil || len(cookie.Value) != 43 {
			writeError(w, 401, "ログインしてください。")
			return
		}
		if r.URL.RawQuery != "" {
			writeError(w, 422, "クエリパラメーターは指定できません。")
			return
		}
		call := application.ProfileCall{Operation: operation, Token: cookie.Value}
		if operation == "save_program" {
			call.CSRF = r.Header.Get("X-CSRF-Token")
			if r.Header.Get("Origin") != origin || len(call.CSRF) != 64 {
				writeError(w, 403, "操作を確認できません。画面を再読み込みしてください。")
				return
			}
			selection, err := decodeSelection(w, r)
			if err != nil {
				writeError(w, 422, "所属・カリキュラム・更新版を正しい形式で指定してください。")
				return
			}
			call.Selection = selection
		}
		result, err := gateway.Call(r.Context(), call)
		if err != nil {
			var business *application.AuthError
			if errors.As(err, &business) {
				switch business.Code {
				case "invalid_credentials", "invalid_csrf":
					writeAuthError(w, business.Code)
				case "invalid_program":
					writeError(w, 422, "所属とカリキュラムの組合せが不正です。選択肢を再取得してください。")
				case "revision_conflict":
					writeError(w, 409, "別の画面でデータが更新されました。再取得してから保存してください。")
				case "profile_not_found":
					writeError(w, 401, "ログインしてください。")
				case "profile_unavailable", "auth_unavailable":
					writeError(w, 503, "所属情報を処理できません。時間をおいて再試行してください。")
				default:
					writeError(w, 502, "所属サービスの応答を読み込めません。")
				}
			} else {
				writeError(w, 502, "所属サービスに接続できません。時間をおいて再試行してください。")
			}
			return
		}
		if operation == "programs" {
			writeJSON(w, 200, result)
		} else {
			writeJSON(w, 200, result.Profile)
		}
	})
}

func decodeSelection(w http.ResponseWriter, r *http.Request) (*application.ProgramSelection, error) {
	invalid := errors.New("invalid selection")
	media, _, err := mime.ParseMediaType(r.Header.Get("Content-Type"))
	if err != nil || media != "application/json" {
		return nil, invalid
	}
	decoder := json.NewDecoder(http.MaxBytesReader(w, r.Body, 4096))
	token, err := decoder.Token()
	if err != nil || token != json.Delim('{') {
		return nil, invalid
	}
	fields := map[string]json.RawMessage{}
	for decoder.More() {
		token, err := decoder.Token()
		if err != nil {
			return nil, invalid
		}
		key, ok := token.(string)
		if !ok || fields[key] != nil {
			return nil, invalid
		}
		var value json.RawMessage
		if decoder.Decode(&value) != nil || string(value) == "null" {
			return nil, invalid
		}
		fields[key] = value
	}
	if token, err = decoder.Token(); err != nil || token != json.Delim('}') || len(fields) != 3 {
		return nil, invalid
	}
	var extra any
	if decoder.Decode(&extra) != io.EOF {
		return nil, invalid
	}
	var selection application.ProgramSelection
	if json.Unmarshal(fields["program_id"], &selection.ProgramID) != nil || json.Unmarshal(fields["curriculum_id"], &selection.CurriculumID) != nil || json.Unmarshal(fields["expected_revision"], &selection.ExpectedRevision) != nil || selection.ExpectedRevision < 0 || selection.ExpectedRevision > 9007199254740990 {
		return nil, invalid
	}
	selection.ProgramID, err = normalizeUUID(selection.ProgramID)
	if err != nil {
		return nil, invalid
	}
	selection.CurriculumID, err = normalizeUUID(selection.CurriculumID)
	if err != nil {
		return nil, invalid
	}
	return &selection, nil
}
