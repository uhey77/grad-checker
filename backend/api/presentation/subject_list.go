// 開発用科目一覧APIと稼働確認API。
package presentation

import (
	"encoding/json"
	"errors"
	"net/http"
	"strings"

	"grad-checker/backend/modules/subjects/application/ports"
)

func NewSubjectListHandler(reader ports.SubjectListReader, preview bool) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		const prefix = "/api/dev/subject-list/"
		path := r.URL.Path
		subjectList := strings.HasPrefix(path, prefix) && len(path) > len(prefix) && !strings.Contains(strings.TrimPrefix(path, prefix), "/")
		if path != "/api/health" && !subjectList {
			writeError(w, 404, "APIが見つかりません。")
			return
		}
		if !allowMethod(w, r, http.MethodGet) {
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

func writeSubjectListError(w http.ResponseWriter, err error) {
	var business *ports.SubjectListError
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
	if errors.Is(err, ports.ErrTimeout) {
		writeError(w, 504, "Pythonサービスの応答がタイムアウトしました。")
		return
	}
	if errors.Is(err, ports.ErrUnavailable) {
		writeError(w, 502, "Pythonサービスに接続できません。起動状態を確認してください。")
		return
	}
	writeError(w, 502, "Pythonサービスの応答を読み込めません。")
}
