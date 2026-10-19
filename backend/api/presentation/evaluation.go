package presentation

import (
	"errors"
	"net/http"

	"grad-checker/backend/modules/requirements/application"
)

func NewEvaluationHandler(gateway application.EvaluationGateway, fallback http.Handler) http.Handler {
	return newEvaluationHandler("/api/me/graduation-requirements", gateway, fallback)
}

func NewDashboardHandler(gateway application.EvaluationGateway, fallback http.Handler) http.Handler {
	return newEvaluationHandler("/api/me/dashboard", gateway, fallback)
}

func newEvaluationHandler(path string, gateway application.EvaluationGateway, fallback http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != path {
			fallback.ServeHTTP(w, r)
			return
		}
		w.Header().Set("Cache-Control", "no-store")
		if !allowMethod(w, r, http.MethodGet) {
			return
		}
		token, ok := requireSession(w, r)
		if !ok || rejectQuery(w, r) {
			return
		}
		result, err := gateway.Call(r.Context(), application.EvaluationCall{Token: token})
		if err != nil {
			writeEvaluationError(w, err)
			return
		}
		writeJSON(w, 200, result)
	})
}

func writeEvaluationError(w http.ResponseWriter, err error) {
	var failure *application.EvaluationError
	if !errors.As(err, &failure) {
		writeError(w, 502, "卒業要件の判定サービスに接続できません。時間をおいて再試行してください。")
		return
	}
	if writeSharedError(w, failure.Code, "卒業要件の判定") {
		return
	}
	details := map[string]string{
		"program_not_selected":                 "所属が未設定です。所属設定を保存してから判定してください。",
		"unverified_credit_rule":               "必要な単位換算・他学部算入の規則が未確認のため、卒業要件を判定できません。",
		"external_acquisition_period_required": "他学部科目の算入先を決めるため、履修年度・学期が必要です。他学部科目の未入力の年度・学期を入力して保存し、再度判定してください。",
		"unsupported_external_credits":         "所属課程外の修得科目に、算入先が未登録の科目があります。対象科目と算入先のマスタ整備が必要です。",
		"invalid_evaluation_master":            "卒業要件の科目・条件・算入規則の設定が不足しているか、不整合があります。",
		"unverified_completion_policy":         "課程の科目・修了条件・算入規則に未確認事項があります。所属一覧の確認状況と根拠を確認してください。",
		"invalid_completion_answers":           "修了条件の回答が重複しているか、選択した課程の条件ではありません。",
		"invalid_evaluation_input":             "保存済みの成績または判定マスタが不正なため、判定できません。",
		"invalid_grades":                       "保存済みの成績データが不正なため、判定できません。",
		"invalid_attempt_sequence":             "保存済みの履修回次が不正なため、判定できません。",
		"duplicate_attempt":                    "保存済みの履修回次が重複しているため、判定できません。",
	}
	if detail, ok := details[failure.Code]; ok {
		writeError(w, 409, detail)
		return
	}
	if failure.Code == "unknown_course" {
		writeError(w, 400, "保存済みの成績に未知の科目が含まれています。")
		return
	}
	writeError(w, 502, "卒業要件の判定サービスの応答を読み込めません。")
}
