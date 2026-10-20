package controllers

import "grad-checker/backend/apps/api/middleware"

import "grad-checker/backend/apps/api/schemas"

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
			schemas.WriteError(w, 404, "APIが見つかりません。")
			return
		}
		if !middleware.AllowMethod(w, r, http.MethodGet) {
			return
		}
		if path == "/api/health" {
			schemas.WriteJSON(w, 200, map[string]string{"status": "ok"})
			return
		}
		if !preview {
			schemas.WriteError(w, 404, "科目一覧の開発用表示は無効です。")
			return
		}
		id := strings.TrimPrefix(path, prefix)
		var data json.RawMessage
		var err error
		if id == "programs" {
			data, err = reader.ListPrograms(r.Context())
		} else {
			id, err = schemas.NormalizeUUID(id)
			if err != nil {
				schemas.WriteError(w, 422, "カリキュラムIDの形式が不正です。")
				return
			}
			data, err = reader.GetSubjectList(r.Context(), id)
		}
		if err != nil {
			writeSubjectListError(w, err)
			return
		}
		schemas.WriteJSON(w, 200, data)
	})
}

func writeSubjectListError(w http.ResponseWriter, err error) {
	var business *ports.SubjectListError
	if errors.As(err, &business) {
		switch business.Code {
		case "curriculum_not_found":
			schemas.WriteError(w, 404, "選択したカリキュラムが見つかりません。")
			return
		case "classification_inconsistent":
			schemas.WriteError(w, 409, "科目分類のデータが不整合です。課程・科目データを確認してください。")
			return
		case "subject_list_unavailable":
			schemas.WriteError(w, 503, "科目データを読み込めません。時間をおいて再試行してください。")
			return
		case "internal_error":
			schemas.WriteError(w, 500, "科目データの取得中に予期しないエラーが発生しました。")
			return
		}
	}
	if errors.Is(err, ports.ErrTimeout) {
		schemas.WriteError(w, 504, "Pythonサービスの応答がタイムアウトしました。")
		return
	}
	if errors.Is(err, ports.ErrUnavailable) {
		schemas.WriteError(w, 502, "Pythonサービスに接続できません。起動状態を確認してください。")
		return
	}
	schemas.WriteError(w, 502, "Pythonサービスの応答を読み込めません。")
}
