package tests

import (
	"context"
	"encoding/json"
	"fmt"
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
		{"未認証の一覧", "GET", "/api/checks", "", false, false, "", 401, 0},
		{"一覧の削除", "DELETE", "/api/checks", "", true, true, "", 405, 0},
		{"詳細のクエリ", "GET", detail + "?limit=1", "", true, false, "", 422, 0},
		{"詳細の更新", "PUT", detail, "", true, true, "", 405, 0},
		{"Origin・CSRFなし", "POST", "/api/checks", valid, true, false, "", 403, 0},
		{"本人IDの指定", "POST", "/api/checks?student_id=x", valid, true, true, "", 422, 0},
		{"未知フィールド", "POST", "/api/checks", `{"expected_revision":3,"student_id":"x"}`, true, true, "", 422, 0},
		{"負の版", "POST", "/api/checks", `{"expected_revision":-1}`, true, true, "", 422, 0},
		{"版の不足", "POST", "/api/checks", `{}`, true, true, "", 422, 0},
		{"本文が大きすぎる", "POST", "/api/checks", `{"expected_revision":3` + strings.Repeat(" ", 32<<10) + `}`, true, true, "", 413, 0},
		{"不正なID", "GET", "/api/checks/not-a-uuid", "", true, false, "", 404, 0},
		{"保存", "POST", "/api/checks", valid, true, true, "", 201, 1},
		{"取得", "GET", detail, "", true, false, "", 200, 1},
		{"他人・存在しない履歴", "GET", detail, "", true, false, "check_not_found", 404, 1},
		{"一覧", "GET", "/api/checks", "", true, false, "", 200, 1},
		{"一覧の保存失敗", "GET", "/api/checks", "", true, false, "check_unavailable", 503, 1},
		{"一覧の不正な保存データ", "GET", "/api/checks", "", true, false, "invalid_check_result", 502, 1},
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
		if tc.path == detail && (call.Operation != "get" || call.CheckID != checkID || call.Request != nil || call.Page != nil || call.CSRF != "") {
			t.Fatalf("%s: %+v", tc.name, call)
		}
		if tc.method == "GET" && tc.path == "/api/checks" && (call.Operation != "list" || call.Page == nil || call.CheckID != "" || call.Request != nil || call.CSRF != "") {
			t.Fatalf("%s: %+v", tc.name, call)
		}
	}
}

func TestCheckHandlerListPaging(t *testing.T) {
	for _, tc := range []struct {
		query         string
		status        int
		limit, offset int64
	}{
		{"", 200, 20, 0},
		{"limit=1", 200, 1, 0},
		{"limit=100&offset=40", 200, 100, 40},
		{"offset=9007199254740990", 200, 20, 9007199254740990},
		{"limit=0", 422, 0, 0},
		{"limit=101", 422, 0, 0},
		{"offset=-1", 422, 0, 0},
		{"limit=%2B5", 422, 0, 0},
		{"limit=1.5", 422, 0, 0},
		{"limit=", 422, 0, 0},
		{"limit=1&limit=2", 422, 0, 0},
		{"offset=9007199254740991", 422, 0, 0},
		{"student_id=x", 422, 0, 0},
		{"limit=%zz", 422, 0, 0},
	} {
		fake := &fakeChecks{}
		recorder := httptest.NewRecorder()
		presentation.NewCheckHandler(fake, checkOrigin, http.NotFoundHandler()).ServeHTTP(recorder, checkRequest("GET", "/api/checks?"+tc.query, "", true, false))
		if recorder.Code != tc.status {
			t.Fatalf("%s: %d %s", tc.query, recorder.Code, recorder.Body.String())
		}
		if tc.status != 200 {
			if len(fake.calls) != 0 || !strings.Contains(recorder.Body.String(), "limitは1〜100") {
				t.Fatalf("%s: %s", tc.query, recorder.Body.String())
			}
			continue
		}
		page := fake.calls[0].Page
		if fake.calls[0].Operation != "list" || page == nil || page.Limit != tc.limit || page.Offset != tc.offset {
			t.Fatalf("%s: %+v", tc.query, fake.calls[0])
		}
	}
}

const checkData = `{"id":"` + checkID + `","created_at":"2026-10-16T00:00:00Z","input":{"program_id":"p","curriculum_id":"c1","data_revision":1,"grades":[]},"result":` + evaluationData + `}`

const checkSummary = `{"id":"` + checkID + `","created_at":"2026-10-16T00:00:00Z","data_revision":1,"result":"fail","curriculum":{"id":"c1","code":"cs","name":"課程","revision":3},"total":{"required_credits":124,"earned_credits":10,"credited_credits":10,"shortage":114,"result":"fail"}}`

func checkList(items string, limit, offset, total int) string {
	return fmt.Sprintf(`{"checks":[%s],"limit":%d,"offset":%d,"total_count":%d}`, items, limit, offset, total)
}

func TestCheckClientEnvelopeAndInvalidResponses(t *testing.T) {
	create := application.CheckCall{Operation: "create", Token: "token", CSRF: strings.Repeat("c", 64), Request: &application.CheckRequest{ExpectedRevision: 1}}
	get := application.CheckCall{Operation: "get", Token: "token", CheckID: checkID}
	list := application.CheckCall{Operation: "list", Token: "token", Page: &application.CheckPage{Limit: 1, Offset: 2}}
	for _, tc := range []struct {
		name     string
		call     application.CheckCall
		response string
		good     bool
	}{
		{"保存", create, `{"data":` + checkData + `}`, true},
		{"取得", get, `{"data":` + checkData + `}`, true},
		{"推薦導入前の履歴取得", get, `{"data":` + strings.Replace(checkData, `"recommendations":[],`, ``, 1) + `}`, true},
		{"要求と異なる版", application.CheckCall{Operation: "create", Token: "token", CSRF: strings.Repeat("c", 64), Request: &application.CheckRequest{ExpectedRevision: 2}}, `{"data":` + checkData + `}`, false},
		{"要求と異なるID", application.CheckCall{Operation: "get", Token: "token", CheckID: "00000000-0000-4000-8000-000000000002"}, `{"data":` + checkData + `}`, false},
		{"入力と結果の版の不一致", get, `{"data":` + strings.Replace(checkData, `"data_revision":1,"grades"`, `"data_revision":2,"grades"`, 1) + `}`, false},
		{"結果の欠落", get, `{"data":` + strings.Replace(checkData, `"result":`+evaluationData, `"result":{}`, 1) + `}`, false},
		{"作成日時の不正", get, `{"data":` + strings.Replace(checkData, `2026-10-16T00:00:00Z","input"`, `yesterday","input"`, 1) + `}`, false},
		{"一覧", list, `{"data":` + checkList(checkSummary, 1, 2, 3) + `}`, true},
		{"範囲外の空の一覧", list, `{"data":` + checkList("", 1, 2, 0) + `}`, true},
		{"件数の上限超過", list, `{"data":` + checkList(checkSummary+","+checkSummary, 1, 2, 4) + `}`, false},
		{"要求と異なる範囲", list, `{"data":` + checkList(checkSummary, 1, 0, 3) + `}`, false},
		{"総件数との矛盾", list, `{"data":` + checkList(checkSummary, 1, 2, 2) + `}`, false},
		{"一覧の欠落", list, `{"data":{"limit":1,"offset":2,"total_count":0}}`, false},
		{"要約の判定の不正", list, `{"data":` + checkList(strings.Replace(checkSummary, `"result":"fail","curriculum"`, `"result":"ok","curriculum"`, 1), 1, 2, 3) + `}`, false},
		{"要約の単位の欠落", list, `{"data":` + checkList(strings.Replace(checkSummary, `"shortage":114,`, ``, 1), 1, 2, 3) + `}`, false},
		{"要約の課程名の欠落", list, `{"data":` + checkList(strings.Replace(checkSummary, `"name":"課程",`, ``, 1), 1, 2, 3) + `}`, false},
		{"要約の作成日時の不正", list, `{"data":` + checkList(strings.Replace(checkSummary, `2026-10-16T00:00:00Z`, `yesterday`, 1), 1, 2, 3) + `}`, false},
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
		if tc.good && tc.call.Operation != "list" && tc.response != `{"data":`+string(data)+`}` {
			t.Fatalf("%s: %s", tc.name, data)
		}
		if err != nil && strings.Contains(err.Error(), "SQL") {
			t.Fatalf("%s: leaked error", tc.name)
		}
	}
}

func TestCompletionAnswerInputValidation(t *testing.T) {
	for _, tc := range []struct {
		body   string
		status int
	}{
		{`{"expected_revision":1,"completion_answers":[{"code":"thesis","status":"met"}]}`, 201},
		{`{"expected_revision":1,"completion_answers":[]}`, 201},
		{`{"expected_revision":1,"completion_answers":null}`, 422},
		{`{"expected_revision":1,"completion_answers":[{"code":"thesis","status":true}]}`, 422},
		{`{"expected_revision":1,"completion_answers":[{"code":"thesis","status":"met"},{"code":"thesis","status":"unknown"}]}`, 422},
		{`{"expected_revision":1,"completion_answers":[{"code":"thesis","status":"met","student_id":"other"}]}`, 422},
		{`{"expected_revision":1,"completion_answers":[{"code":"thesis","status":"yes"}]}`, 422},
		{`{"expected_revision":1,"completion_answers":[],"completion_answers":[]}`, 422},
	} {
		gateway := &fakeChecks{}
		handler := presentation.NewCheckHandler(gateway, checkOrigin, http.NotFoundHandler())
		response := httptest.NewRecorder()
		handler.ServeHTTP(response, checkRequest("POST", "/api/checks", tc.body, true, true))
		if response.Code != tc.status {
			t.Fatalf("%s: %d %s", tc.body, response.Code, response.Body.String())
		}
		if tc.status == 201 && strings.Contains(tc.body, `"thesis"`) {
			if len(gateway.calls) != 1 || len(gateway.calls[0].Request.CompletionAnswers) != 1 || gateway.calls[0].Request.CompletionAnswers[0].Status != "met" {
				t.Fatal("修了条件がブリッジへ渡されていない")
			}
		}
	}
}
