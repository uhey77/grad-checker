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

type fakeEvaluation struct {
	calls []application.EvaluationCall
	err   error
}

func (f *fakeEvaluation) Call(_ context.Context, call application.EvaluationCall) (json.RawMessage, error) {
	f.calls = append(f.calls, call)
	return json.RawMessage(`{"result":"fail"}`), f.err
}

func evaluationRequest(method, path string, authenticated bool) *http.Request {
	request := httptest.NewRequest(method, path, nil)
	if authenticated {
		request.AddCookie(&http.Cookie{Name: "grad_checker_session", Value: strings.Repeat("s", 43)})
	}
	return request
}

func TestEvaluationHandlerAuthorizationAndErrors(t *testing.T) {
	for endpoint, newHandler := range map[string]func(application.EvaluationGateway, http.Handler) http.Handler{
		"/api/me/graduation-requirements": presentation.NewEvaluationHandler,
		"/api/me/dashboard":               presentation.NewDashboardHandler,
	} {
		for _, tc := range []struct {
			method, path  string
			auth          bool
			code          string
			status, calls int
		}{
			{"GET", endpoint, false, "", 401, 0},
			{"PUT", endpoint, true, "", 405, 0},
			{"GET", endpoint + "?student_id=other", true, "", 422, 0},
			{"GET", "/api/unknown", true, "", 404, 0},
			{"GET", endpoint, true, "", 200, 1},
			{"GET", endpoint, true, "invalid_credentials", 401, 1},
			{"GET", endpoint, true, "unverified_credit_rule", 409, 1},
			{"GET", endpoint, true, "external_acquisition_period_required", 409, 1},
			{"GET", endpoint, true, "unsupported_external_credits", 409, 1},
			{"GET", endpoint, true, "invalid_evaluation_master", 409, 1},
			{"GET", endpoint, true, "unknown_course", 400, 1},
			{"GET", endpoint, true, "evaluation_unavailable", 503, 1},
			{"GET", endpoint, true, "internal_error", 502, 1},
		} {
			fake := &fakeEvaluation{}
			if tc.code != "" {
				fake.err = &application.EvaluationError{Code: tc.code}
			}
			recorder := httptest.NewRecorder()
			newHandler(fake, http.NotFoundHandler()).ServeHTTP(recorder, evaluationRequest(tc.method, tc.path, tc.auth))
			if recorder.Code != tc.status || len(fake.calls) != tc.calls {
				t.Fatalf("%+v: %d %s", tc, recorder.Code, recorder.Body.String())
			}
			if tc.path == endpoint && recorder.Header().Get("Cache-Control") != "no-store" {
				t.Fatal("missing cache control")
			}
			if tc.calls == 1 && fake.calls[0].Token != strings.Repeat("s", 43) {
				t.Fatal("missing token")
			}
			if tc.status >= 400 && strings.Contains(recorder.Body.String(), `"result"`) {
				t.Fatal("error became a judgment")
			}
		}
	}

}

const evaluationData = `{"result":"fail","data_revision":1,"evaluated_at":"2026-10-16T00:00:00Z","curriculum":{"id":"c1","revision":1},"total":{"required_credits":10,"earned_credits":0,"credited_credits":0,"shortage":10,"result":"fail"},"requirements":[{}],"categories":[],"missing_required_courses":[],"courses":[],"allocations":[],"external_allocations":[],"warnings":[],"rule_revisions":{}}`

func TestEvaluationClientEnvelopeAndInvalidResponses(t *testing.T) {
	for _, tc := range []struct {
		response string
		good     bool
	}{
		{`{"data":` + evaluationData + `}`, true},
		{`{"data":{}}`, false},
		{`{"data":` + strings.Replace(evaluationData, `"fail"`, `"unknown"`, 1) + `}`, false},
		{`{"data":` + strings.Replace(evaluationData, `"data_revision":1`, `"data_revision":null`, 1) + `}`, false},
		{`{"data":` + strings.Replace(evaluationData, `"missing_required_courses":[]`, `"missing_required_courses":null`, 1) + `}`, false},
		{`{"error":{"code":"unverified_credit_rule","detail":"private SQL"}}`, false},
	} {
		server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if r.URL.Path != "/bridge/graduation-requirements" {
				t.Error(r.URL.Path)
			}
			var body map[string]string
			_ = json.NewDecoder(r.Body).Decode(&body)
			if len(body) != 1 || body["token"] != "token" {
				t.Error(body)
			}
			_, _ = w.Write([]byte(tc.response))
		}))
		client, err := infrastructure.NewPythonEvaluationClient(server.URL)
		if err != nil {
			t.Fatal(err)
		}
		data, err := client.Call(context.Background(), application.EvaluationCall{Token: "token"})
		server.Close()
		if (err == nil) != tc.good {
			t.Fatalf("%s: %v", tc.response, err)
		}
		if tc.good && string(data) != evaluationData {
			t.Fatal(string(data))
		}
		if err != nil && strings.Contains(err.Error(), "SQL") {
			t.Fatal("leaked error")
		}
	}
}

const dashboardData = `{"result":"fail","data_revision":1,"curriculum_revision":1,"grade_count":0,"evaluated_at":"2026-10-18T00:00:00Z","curriculum":{"id":"c1","revision":1},"total":{"required_credits":10,"earned_credits":0,"credited_credits":0,"shortage":10,"result":"fail"},"categories":[],"warnings":[],"rule_revisions":{}}`

func TestDashboardClientRejectsInvalidSummary(t *testing.T) {
	responses := []struct {
		body string
		good bool
	}{
		{`{"data":` + dashboardData + `}`, true},
		{`{"data":{}}`, false},
		{`{"data":` + strings.Replace(dashboardData, `"curriculum_revision":1`, `"curriculum_revision":2`, 1) + `}`, false},
		{`{"data":` + strings.Replace(dashboardData, `"grade_count":0`, `"grade_count":null`, 1) + `}`, false},
		{`{"data":` + strings.Replace(dashboardData, `"categories":[]`, `"categories":null`, 1) + `}`, false},
		{`{"data":` + strings.Replace(dashboardData, `"shortage":10`, `"shortage":-1`, 1) + `}`, false},
		{`{"data":` + strings.Replace(dashboardData, `2026-10-18T00:00:00Z`, `invalid`, 1) + `}`, false},
		{`{"error":{"code":"evaluation_unavailable","detail":"private SQL"}}`, false},
	}
	for _, tc := range responses {
		server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if r.Method != "POST" || r.URL.Path != "/bridge/dashboard" {
				t.Error(r.Method, r.URL.Path)
			}
			var call application.EvaluationCall
			if json.NewDecoder(r.Body).Decode(&call) != nil || call.Token != "token" {
				t.Error("missing identity")
			}
			_, _ = w.Write([]byte(tc.body))
		}))
		client, err := infrastructure.NewPythonDashboardClient(server.URL)
		if err != nil {
			t.Fatal(err)
		}
		result, err := client.Call(context.Background(), application.EvaluationCall{Token: "token"})
		server.Close()
		if (err == nil) != tc.good {
			t.Fatalf("%s: %v", tc.body, err)
		}
		if tc.good && string(result) != dashboardData {
			t.Fatal(string(result))
		}
		if err != nil && strings.Contains(err.Error(), "SQL") {
			t.Fatal("leaked error")
		}
	}
}
