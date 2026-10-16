package presentation

import (
	"errors"
	"net/http"

	"grad-checker/backend/modules/accounts/application"
)

const selectionDetail = "所属・カリキュラム・更新版を正しい形式で指定してください。"

// 本人IDを外部入力から受け取らず、セッション原値をPythonサービスで検証する。
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
		if !allowMethod(w, r, method) {
			return
		}
		token, ok := requireSession(w, r)
		if !ok || rejectQuery(w, r) {
			return
		}
		call := application.ProfileCall{Operation: operation, Token: token}
		if operation == "save_program" {
			csrf, ok := writeToken(w, r, origin)
			if !ok {
				return
			}
			body, ok := readJSONBody(w, r, 4096, selectionDetail)
			if !ok {
				return
			}
			selection, ok := decodeSelection(body)
			if !ok {
				writeError(w, 422, selectionDetail)
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
			writeJSON(w, 200, result)
		} else {
			writeJSON(w, 200, result.Profile)
		}
	})
}

func writeProfileError(w http.ResponseWriter, err error) {
	var business *application.AuthError
	if !errors.As(err, &business) {
		writeError(w, 502, "所属サービスに接続できません。時間をおいて再試行してください。")
		return
	}
	if writeSharedError(w, business.Code, "所属情報") {
		return
	}
	if business.Code == "invalid_program" {
		writeError(w, 422, "所属とカリキュラムの組合せが不正です。選択肢を再取得してください。")
		return
	}
	writeError(w, 502, "所属サービスの応答を読み込めません。")
}

func decodeSelection(body []byte) (*application.ProgramSelection, bool) {
	fields, ok := strictObject(body, "program_id", "curriculum_id", "expected_revision")
	if !ok {
		return nil, false
	}
	var selection application.ProgramSelection
	if selection.ProgramID, ok = decodeUUID(fields["program_id"]); !ok {
		return nil, false
	}
	if selection.CurriculumID, ok = decodeUUID(fields["curriculum_id"]); !ok {
		return nil, false
	}
	if selection.ExpectedRevision, ok = decodeInt(fields["expected_revision"], 0, maxSafeRevision); !ok {
		return nil, false
	}
	return &selection, true
}
