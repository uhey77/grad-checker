package controllers

import "grad-checker/backend/apps/api/middleware"

import "grad-checker/backend/apps/api/schemas"

import (
	"errors"
	"net/http"

	"strings"

	"grad-checker/backend/modules/requirements/application/ports"
)

// 本人の判定を保存し（POST /api/checks）、本人の履歴を一覧し（GET /api/checks）、
// 保存済みの履歴を本人に限って返す（GET /api/checks/{id}）。
func NewCheckHandler(gateway ports.CheckGateway, origin string, fallback http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		path := r.URL.Path
		if path != schemas.ChecksPath && !strings.HasPrefix(path, schemas.ChecksPath+"/") {
			fallback.ServeHTTP(w, r)
			return
		}
		w.Header().Set("Cache-Control", "no-store")
		collection := path == schemas.ChecksPath
		methods := []string{http.MethodGet}
		if collection {
			methods = append(methods, http.MethodPost)
		}
		if !middleware.AllowMethod(w, r, methods...) {
			return
		}
		token, ok := middleware.RequireSession(w, r)
		if !ok {
			return
		}
		call, status := ports.CheckCall{Token: token}, 200
		switch {
		case r.Method == http.MethodPost:
			if middleware.RejectQuery(w, r) {
				return
			}
			csrf, ok := middleware.WriteToken(w, r, origin)
			if !ok {
				return
			}
			body, ok := middleware.ReadJSONBody(w, r, schemas.MaxCheckBody, "送信内容が上限を超えています。")
			if !ok {
				return
			}
			fields, ok := schemas.StrictObject(body, "expected_revision", "completion_answers")
			if !ok {
				fields, ok = schemas.StrictObject(body, "expected_revision")
			}
			if !ok {
				schemas.WriteError(w, 422, schemas.CheckBodyDetail)
				return
			}
			revision, ok := schemas.DecodeInt(fields["expected_revision"], 0, schemas.MaxSafeRevision)
			if !ok {
				schemas.WriteError(w, 422, schemas.CheckBodyDetail)
				return
			}
			call.Operation, call.CSRF, status = "create", csrf, 201
			answers, valid := schemas.ParseCompletionAnswers(fields["completion_answers"])
			if !valid {
				schemas.WriteError(w, 422, schemas.CheckBodyDetail)
				return
			}
			call.Request = &ports.CheckRequest{ExpectedRevision: revision, CompletionAnswers: answers}
		case collection:
			page, ok := schemas.ParseCheckPage(r.URL.RawQuery)
			if !ok {
				schemas.WriteError(w, 422, schemas.CheckPageDetail)
				return
			}
			call.Operation, call.Page = "list", page
		default:
			if middleware.RejectQuery(w, r) {
				return
			}
			// 形式が不正なIDも、他人・存在しないIDと同じ404にする。
			id, err := schemas.NormalizeUUID(strings.TrimPrefix(path, schemas.ChecksPath+"/"))
			if err != nil {
				schemas.WriteError(w, 404, schemas.CheckNotFound)
				return
			}
			call.Operation, call.CheckID = "get", id
		}
		result, err := gateway.Call(r.Context(), call)
		if err != nil {
			writeCheckError(w, err)
			return
		}
		schemas.WriteJSON(w, status, result)
	})
}

func writeCheckError(w http.ResponseWriter, err error) {
	var failure *ports.EvaluationError
	if errors.As(err, &failure) {
		if writeSharedError(w, failure.Code, "判定履歴") {
			return
		}
		if failure.Code == "check_not_found" {
			schemas.WriteError(w, 404, schemas.CheckNotFound)
			return
		}
	}
	writeEvaluationError(w, err)
}
