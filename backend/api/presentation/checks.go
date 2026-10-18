package presentation

import (
	"errors"
	"net/http"
	"net/url"
	"strconv"
	"strings"

	"grad-checker/backend/modules/requirements/application"
)

const (
	checksPath       = "/api/checks"
	maxCheckBody     = 1 << 10
	defaultCheckPage = 20
	maxCheckPage     = 100
	checkNotFound    = "判定履歴が見つかりません。"
	checkBodyDetail  = "判定の送信形式が不正です。expected_revisionだけを指定してください。"
	checkPageDetail  = "履歴の表示範囲が不正です。limitは1〜100、offsetは0以上の整数で各1回まで指定してください。"
)

// 本人の判定を保存し（POST /api/checks）、本人の履歴を一覧し（GET /api/checks）、
// 保存済みの履歴を本人に限って返す（GET /api/checks/{id}）。
func NewCheckHandler(gateway application.CheckGateway, origin string, fallback http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		path := r.URL.Path
		if path != checksPath && !strings.HasPrefix(path, checksPath+"/") {
			fallback.ServeHTTP(w, r)
			return
		}
		w.Header().Set("Cache-Control", "no-store")
		collection := path == checksPath
		methods := []string{http.MethodGet}
		if collection {
			methods = append(methods, http.MethodPost)
		}
		if !allowMethod(w, r, methods...) {
			return
		}
		token, ok := requireSession(w, r)
		if !ok {
			return
		}
		call, status := application.CheckCall{Token: token}, 200
		switch {
		case r.Method == http.MethodPost:
			if rejectQuery(w, r) {
				return
			}
			csrf, ok := writeToken(w, r, origin)
			if !ok {
				return
			}
			body, ok := readJSONBody(w, r, maxCheckBody, "送信内容が上限を超えています。")
			if !ok {
				return
			}
			fields, ok := strictObject(body, "expected_revision")
			if !ok {
				writeError(w, 422, checkBodyDetail)
				return
			}
			revision, ok := decodeInt(fields["expected_revision"], 0, maxSafeRevision)
			if !ok {
				writeError(w, 422, checkBodyDetail)
				return
			}
			call.Operation, call.CSRF, status = "create", csrf, 201
			call.Request = &application.CheckRequest{ExpectedRevision: revision}
		case collection:
			page, ok := parseCheckPage(r.URL.RawQuery)
			if !ok {
				writeError(w, 422, checkPageDetail)
				return
			}
			call.Operation, call.Page = "list", page
		default:
			if rejectQuery(w, r) {
				return
			}
			// 形式が不正なIDも、他人・存在しないIDと同じ404にする。
			id, err := normalizeUUID(strings.TrimPrefix(path, checksPath+"/"))
			if err != nil {
				writeError(w, 404, checkNotFound)
				return
			}
			call.Operation, call.CheckID = "get", id
		}
		result, err := gateway.Call(r.Context(), call)
		if err != nil {
			writeCheckError(w, err)
			return
		}
		writeJSON(w, status, result)
	})
}

// parseCheckPageは一覧のlimit（既定20、1〜100）とoffset（既定0）を10進数の整数で受け付ける。
func parseCheckPage(rawQuery string) (*application.CheckPage, bool) {
	query, err := url.ParseQuery(rawQuery)
	if err != nil {
		return nil, false
	}
	page := &application.CheckPage{Limit: defaultCheckPage}
	for key, values := range query {
		if len(values) != 1 {
			return nil, false
		}
		var ok bool
		switch key {
		case "limit":
			page.Limit, ok = parseDecimal(values[0], 1, maxCheckPage)
		case "offset":
			page.Offset, ok = parseDecimal(values[0], 0, maxSafeRevision)
		}
		if !ok {
			return nil, false
		}
	}
	return page, true
}

// parseDecimalは符号・空白・小数を含まない10進数の整数だけを範囲内で受け付ける。
func parseDecimal(value string, minimum, maximum int64) (int64, bool) {
	if value == "" || strings.Trim(value, "0123456789") != "" {
		return 0, false
	}
	number, err := strconv.ParseInt(value, 10, 64)
	return number, err == nil && number >= minimum && number <= maximum
}

func writeCheckError(w http.ResponseWriter, err error) {
	var failure *application.EvaluationError
	if errors.As(err, &failure) {
		if writeSharedError(w, failure.Code, "判定履歴") {
			return
		}
		if failure.Code == "check_not_found" {
			writeError(w, 404, checkNotFound)
			return
		}
	}
	writeEvaluationError(w, err)
}
