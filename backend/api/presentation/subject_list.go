// 外部HTTPの入力検証・応答形式・業務エラーのHTTP変換を担当する。
package presentation

import (
	"encoding/hex"
	"encoding/json"
	"errors"
	"net/http"
	"strings"

	"grad-checker/backend/modules/subjects/application"
)

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("Cache-Control", "no-store")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func writeError(w http.ResponseWriter, status int, detail string) {
	writeJSON(w, status, map[string]string{"detail": detail})
}

func NewSubjectListHandler(reader application.SubjectListReader, preview bool) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		const prefix = "/api/dev/subject-list/"
		path := r.URL.Path
		subjectList := strings.HasPrefix(path, prefix) && len(path) > len(prefix) && !strings.Contains(strings.TrimPrefix(path, prefix), "/")
		if path != "/api/health" && !subjectList {
			writeError(w, 404, "APIが見つかりません。")
			return
		}
		if r.Method != http.MethodGet {
			w.Header().Set("Allow", "GET")
			writeError(w, 405, "GETのみ利用できます。")
			return
		}
		if path == "/api/health" {
			writeJSON(w, 200, map[string]string{"status": "ok"})
			return
		}
		if !preview {
			writeError(w, 404, "科目一覧の開発用表示は無効です。")
			return
		}
		id := strings.TrimPrefix(path, prefix)
		var data json.RawMessage
		var err error
		if id == "programs" {
			data, err = reader.ListPrograms(r.Context())
		} else {
			id, err = normalizeUUID(id)
			if err != nil {
				writeError(w, 422, "カリキュラムIDの形式が不正です。")
				return
			}
			data, err = reader.GetSubjectList(r.Context(), id)
		}
		if err != nil {
			writeSubjectListError(w, err)
			return
		}
		writeJSON(w, 200, data)
	})
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

func writeSubjectListError(w http.ResponseWriter, err error) {
	var business *application.SubjectListError
	if errors.As(err, &business) {
		switch business.Code {
		case "curriculum_not_found":
			writeError(w, 404, "選択したカリキュラムが見つかりません。")
			return
		case "classification_inconsistent":
			writeError(w, 409, "科目分類のデータが不整合です。課程・科目データを確認してください。")
			return
		case "subject_list_unavailable":
			writeError(w, 503, "科目データを読み込めません。時間をおいて再試行してください。")
			return
		case "internal_error":
			writeError(w, 500, "科目データの取得中に予期しないエラーが発生しました。")
			return
		}
	}
	if errors.Is(err, application.ErrTimeout) {
		writeError(w, 504, "Pythonサービスの応答がタイムアウトしました。")
		return
	}
	if errors.Is(err, application.ErrUnavailable) {
		writeError(w, 502, "Pythonサービスに接続できません。起動状態を確認してください。")
		return
	}
	writeError(w, 502, "Pythonサービスの応答を読み込めません。")
}
