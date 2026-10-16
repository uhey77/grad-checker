package presentation

import (
	"errors"
	"net/http"
	"net/url"
	"unicode/utf8"

	"grad-checker/backend/modules/subjects/application"
)

var courseFilterKeys = map[string]bool{"category_id": true, "faculty": true, "department": true, "semester": true, "q": true}

// 本人課程から見た科目一覧・分類を返す。本人課程は外部入力ではなくセッションから決める。
func NewCourseHandler(reader application.CourseCatalogReader, fallback http.Handler) http.Handler {
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
		if r.Method != http.MethodGet {
			w.Header().Set("Allow", "GET")
			writeError(w, 405, "GETのみ利用できます。")
			return
		}
		token, ok := sessionToken(r)
		if !ok {
			writeError(w, 401, "ログインしてください。")
			return
		}
		call := application.CourseCatalogCall{Operation: operation, Token: token}
		if operation == "categories" {
			if r.URL.RawQuery != "" {
				writeError(w, 422, "クエリパラメーターは指定できません。")
				return
			}
		} else {
			filters, detail := parseCourseFilters(r.URL.RawQuery)
			if filters == nil {
				writeError(w, 422, detail)
				return
			}
			call.Filters = filters
		}
		data, err := reader.Call(r.Context(), call)
		if err != nil {
			writeCourseError(w, err)
			return
		}
		writeJSON(w, 200, data)
	})
}

func parseCourseFilters(rawQuery string) (*application.CourseFilters, string) {
	query, err := url.ParseQuery(rawQuery)
	if err != nil {
		return nil, "絞り込み条件の形式が不正です。"
	}
	values := map[string]string{}
	for key, list := range query {
		if !courseFilterKeys[key] {
			return nil, "未対応の絞り込み条件が指定されています。"
		}
		if len(list) != 1 || list[0] == "" || utf8.RuneCountInString(list[0]) > 100 {
			return nil, "絞り込み条件は各1回、1〜100文字で指定してください。"
		}
		values[key] = list[0]
	}
	filters := &application.CourseFilters{Faculty: values["faculty"], Department: values["department"], Q: values["q"]}
	if id, ok := values["category_id"]; ok {
		if filters.CategoryID, err = normalizeUUID(id); err != nil {
			return nil, "科目区分IDの形式が不正です。"
		}
	}
	if semester, ok := values["semester"]; ok {
		if semester != "first" && semester != "second" {
			return nil, "開講学期はfirst（前期）またはsecond（後期）で指定してください。"
		}
		filters.Semester = semester
	}
	return filters, ""
}

func writeCourseError(w http.ResponseWriter, err error) {
	var business *application.CourseCatalogError
	if errors.As(err, &business) {
		switch business.Code {
		case "invalid_credentials", "profile_not_found":
			writeAuthError(w, "invalid_credentials")
		case "program_not_selected":
			writeError(w, 409, "所属課程を設定してから科目を表示してください。")
		case "unknown_category":
			writeError(w, 422, "指定した科目区分は本人の課程にありません。科目区分を選び直してください。")
		case "curriculum_not_found":
			writeError(w, 409, "所属課程のデータが見つかりません。所属を設定し直してください。")
		case "classification_inconsistent":
			writeError(w, 409, "科目分類のデータが不整合です。課程・科目データを確認してください。")
		case "catalog_unavailable", "profile_unavailable", "auth_unavailable":
			writeError(w, 503, "科目データを読み込めません。時間をおいて再試行してください。")
		default:
			writeError(w, 502, "科目サービスの応答を読み込めません。")
		}
		return
	}
	if errors.Is(err, application.ErrTimeout) {
		writeError(w, 504, "Pythonサービスの応答がタイムアウトしました。")
		return
	}
	writeError(w, 502, "科目サービスに接続できません。時間をおいて再試行してください。")
}
