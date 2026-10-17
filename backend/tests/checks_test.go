package tests

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"grad-checker/backend/api/presentation"
	"grad-checker/backend/modules/requirements/application"
	"grad-checker/backend/modules/requirements/infrastructure"
)

const (
	checkOrigin = "http://127.0.0.1:5173"
	checkID     = "00000000-0000-4000-8000-000000000001"
)

type fakeChecks struct {
	calls []application.CheckCall
	err   error
}

func (f *fakeChecks) Call(_ context.Context, call application.CheckCall) (json.RawMessage, error) {
	f.calls = append(f.calls, call)
	return json.RawMessage(`{"id":"` + checkID + `"}`), f.err
}

func checkRequest(method, path, body string, auth, csrf bool) *http.Request {
	request := httptest.NewRequest(method, path, strings.NewReader(body))
	request.Header.Set("Content-Type", "application/json")
	if auth {
		request.AddCookie(&http.Cookie{Name: "grad_checker_session", Value: strings.Repeat("s", 43)})
	}
	if csrf {
		request.Header.Set("Origin", checkOrigin)
		request.Header.Set("X-CSRF-Token", strings.Repeat("c", 64))
	}
	return request
}

func TestCheckHandlerValidationAuthorizationAndErrors(t *testing.T) {
	valid := `{"expected_revision":3}`
	detail := "/api/checks/" + checkID
	for _, tc := range []struct {
		name, method, path, body string
		auth, csrf               bool
		code                     string
		status, calls            int
	}{
		{"未認証の保存", "POST", "/api/checks", valid, false, true, "", 401, 0},
		{"未認証の取得", "GET", detail, "", false, false, "", 401, 0},
		{"一覧は未実装", "GET", "/api/checks", "", true, false, "", 405, 0},
		{"詳細の更新", "PUT", detail, "", true, true, "", 405, 0},
		{"Origin・CSRFなし", "POST", "/api/checks", valid, true, false, "", 403, 0},
		{"本人IDの指定", "POST", "/api/checks?student_id=x", valid, true, true, "", 422, 0},
		{"未知フィールド", "POST", "/api/checks", `{"expected_revision":3,"student_id":"x"}`, true, true, "", 422, 0},
		{"負の版", "POST", "/api/checks", `{"expected_revision":-1}`, true, true, "", 422, 0},
		{"版の不足", "POST", "/api/checks", `{}`, true, true, "", 422, 0},
		{"本文が大きすぎる", "POST", "/api/checks", `{"expected_revision":3` + strings.Repeat(" ", 2048) + `}`, true, true, "", 413, 0},
		{"不正なID", "GET", "/api/checks/not-a-uuid", "", true, false, "", 404, 0},
		{"保存", "POST", "/api/checks", valid, true, true, "", 201, 1},
		{"取得", "GET", detail, "", true, false, "", 200, 1},
		{"他人・存在しない履歴", "GET", detail, "", true, false, "check_not_found", 404, 1},
		{"版の競合", "POST", "/api/checks", valid, true, true, "revision_conflict", 409, 1},
		{"CSRF不一致", "POST", "/api/checks", valid, true, true, "invalid_csrf", 403, 1},
		{"所属未設定", "POST", "/api/checks", valid, true, true, "program_not_selected", 409, 1},
		{"未確認規則", "POST", "/api/checks", valid, true, true, "unverified_credit_rule", 409, 1},
		{"保存失敗", "POST", "/api/checks", valid, true, true, "check_unavailable", 503, 1},
		{"予期しない失敗", "POST", "/api/checks", valid, true, true, "internal_error", 502, 1},
		{"他のAPI", "GET", "/api/checksum", "", true, false, "", 404, 0},
	} {
		fake := &fakeChecks{}
		if tc.code != "" {
			fake.err = &application.EvaluationError{Code: tc.code}
		}
		recorder := httptest.NewRecorder()
		presentation.NewCheckHandler(fake, checkOrigin, http.NotFoundHandler()).ServeHTTP(recorder, checkRequest(tc.method, tc.path, tc.body, tc.auth, tc.csrf))
		if recorder.Code != tc.status || len(fake.calls) != tc.calls {
			t.Fatalf("%s: %d %s", tc.name, recorder.Code, recorder.Body.String())
		}
		if tc.name != "他のAPI" && recorder.Header().Get("Cache-Control") != "no-store" {
			t.Fatalf("%s: missing cache control", tc.name)
		}
		if tc.status >= 400 && strings.Contains(recorder.Body.String(), `"result"`) {
			t.Fatalf("%s: error became a judgment", tc.name)
		}
		if tc.calls == 0 {
			continue
		}
		call := fake.calls[0]
		if call.Token != strings.Repeat("s", 43) {
			t.Fatalf("%s: missing token", tc.name)
		}
		if tc.method == "POST" && (call.Operation != "create" || call.CSRF != strings.Repeat("c", 64) || call.Request == nil || call.Request.ExpectedRevision != 3 || call.CheckID != "") {
			t.Fatalf("%s: %+v", tc.name, call)
		}
		if tc.method == "GET" && (call.Operation != "get" || call.CheckID != checkID || call.Request != nil || call.CSRF != "") {
			t.Fatalf("%s: %+v", tc.name, call)
		}
	}
}

const checkData = `{"id":"` + checkID + `","created_at":"2026-10-16T00:00:00Z","input":{"program_id":"p","curriculum_id":"c1","data_revision":1,"grades":[]},"result":` + evaluationData + `}`

func TestCheckClientEnvelopeAndInvalidResponses(t *testing.T) {
	create := application.CheckCall{Operation: "create", Token: "token", CSRF: strings.Repeat("c", 64), Request: &application.CheckRequest{ExpectedRevision: 1}}
	get := application.CheckCall{Operation: "get", Token: "token", CheckID: checkID}
	for _, tc := range []struct {
		name     string
		call     application.CheckCall
		response string
		good     bool
	}{
		{"保存", create, `{"data":` + checkData + `}`, true},
		{"取得", get, `{"data":` + checkData + `}`, true},
		{"要求と異なる版", application.CheckCall{Operation: "create", Token: "token", CSRF: strings.Repeat("c", 64), Request: &application.CheckRequest{ExpectedRevision: 2}}, `{"data":` + checkData + `}`, false},
		{"要求と異なるID", application.CheckCall{Operation: "get", Token: "token", CheckID: "00000000-0000-4000-8000-000000000002"}, `{"data":` + checkData + `}`, false},
		{"入力と結果の版の不一致", get, `{"data":` + strings.Replace(checkData, `"data_revision":1,"grades"`, `"data_revision":2,"grades"`, 1) + `}`, false},
		{"結果の欠落", get, `{"data":` + strings.Replace(checkData, `"result":`+evaluationData, `"result":{}`, 1) + `}`, false},
		{"作成日時の不正", get, `{"data":` + strings.Replace(checkData, `2026-10-16T00:00:00Z","input"`, `yesterday","input"`, 1) + `}`, false},
		{"業務エラー", create, `{"error":{"code":"revision_conflict","detail":"private SQL"}}`, false},
	} {
		server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if r.URL.Path != "/bridge/checks" {
				t.Error(r.URL.Path)
			}
			var body map[string]any
			_ = json.NewDecoder(r.Body).Decode(&body)
			if body["operation"] != tc.call.Operation || body["token"] != "token" {
				t.Error(body)
			}
			_, _ = w.Write([]byte(tc.response))
		}))
		client, err := infrastructure.NewPythonCheckClient(server.URL)
		if err != nil {
			t.Fatal(err)
		}
		data, err := client.Call(context.Background(), tc.call)
		server.Close()
		if (err == nil) != tc.good {
			t.Fatalf("%s: %v", tc.name, err)
		}
		if tc.good && string(data) != checkData {
			t.Fatalf("%s: %s", tc.name, data)
		}
		if err != nil && strings.Contains(err.Error(), "SQL") {
			t.Fatalf("%s: leaked error", tc.name)
		}
	}
}
