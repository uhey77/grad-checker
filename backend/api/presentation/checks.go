package presentation

import (
	"errors"
	"net/http"
	"strings"

	"grad-checker/backend/modules/requirements/application"
)

const (
	checksPath      = "/api/checks"
	maxCheckBody    = 1 << 10
	checkNotFound   = "判定履歴が見つかりません。"
	checkBodyDetail = "判定の送信形式が不正です。expected_revisionだけを指定してください。"
)

// 本人の判定を保存し（POST /api/checks）、保存済みの履歴を本人に限って返す（GET /api/checks/{id}）。
func NewCheckHandler(gateway application.CheckGateway, origin string, fallback http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		path := r.URL.Path
		if path != checksPath && !strings.HasPrefix(path, checksPath+"/") {
			fallback.ServeHTTP(w, r)
			return
		}
		w.Header().Set("Cache-Control", "no-store")
		method, status := http.MethodGet, 200
		if path == checksPath {
			method, status = http.MethodPost, 201
		}
		if !allowMethod(w, r, method) {
			return
		}
		token, ok := requireSession(w, r)
		if !ok || rejectQuery(w, r) {
			return
		}
		call := application.CheckCall{Operation: "get", Token: token}
		if path == checksPath {
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
			call.Operation, call.CSRF = "create", csrf
			call.Request = &application.CheckRequest{ExpectedRevision: revision}
		} else {
			// 形式が不正なIDも、他人・存在しないIDと同じ404にする。
			id, err := normalizeUUID(strings.TrimPrefix(path, checksPath+"/"))
			if err != nil {
				writeError(w, 404, checkNotFound)
				return
			}
			call.CheckID = id
		}
		result, err := gateway.Call(r.Context(), call)
		if err != nil {
			writeCheckError(w, err)
			return
		}
		writeJSON(w, status, result)
	})
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
