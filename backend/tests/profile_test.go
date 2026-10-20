package tests

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"grad-checker/backend/api/presentation"
	"grad-checker/backend/modules/accounts/application/ports"
	"grad-checker/backend/modules/accounts/infrastructure"
)

type fakeProfile struct {
	calls []ports.ProfileCall
	err   error
}

func (f *fakeProfile) Call(_ context.Context, call ports.ProfileCall) (ports.ProfileResult, error) {
	f.calls = append(f.calls, call)
	return ports.ProfileResult{Profile: &ports.Profile{StudentID: "own", LoginName: "owner"}}, f.err
}

const validSelection = `{"program_id":"00000000-0000-4000-8000-000000000001","curriculum_id":"00000000-0000-4000-8000-000000000002","expected_revision":0}`

func TestProfileRejectsInvalidCallsBeforeBackend(t *testing.T) {
	cases := []struct {
		method, path, body, origin, csrf, cookie string
		status                                   int
	}{
		{"GET", "/api/programs", "", "", "", "", 401},
		{"GET", "/api/me", "", "", "", "", 401},
		{"POST", "/api/me", "", "", "", "", 405},
		{"GET", "/api/me?student_id=other", "", "", "", strings.Repeat("s", 43), 422},
		{"PUT", "/api/me/program", validSelection, "https://evil.example", strings.Repeat("c", 64), strings.Repeat("s", 43), 403},
		{"PUT", "/api/me/program", validSelection, "http://127.0.0.1:5173", "", strings.Repeat("s", 43), 403},
	}
	for _, body := range []string{
		`{}`, `null`, `[]`, validSelection + `{}`,
		strings.Replace(validSelection, `"expected_revision":0`, `"expected_revision":null`, 1),
		strings.Replace(validSelection, `"expected_revision":0`, `"expected_revision":true`, 1),
		strings.Replace(validSelection, `"expected_revision":0`, `"expected_revision":-1`, 1),
		strings.Replace(validSelection, `"expected_revision":0`, `"expected_revision":1.5`, 1),
		strings.Replace(validSelection, `"expected_revision":0`, `"expected_revision":9007199254740991`, 1),
		strings.Replace(validSelection, `"expected_revision":0`, `"expected_revision":0,"expected_revision":1`, 1),
		strings.Replace(validSelection, `"expected_revision":0`, `"expected_revision":0,"student_id":"other"`, 1),
		strings.Replace(validSelection, "00000000-0000-4000-8000-000000000001", "unknown", 1),
	} {
		cases = append(cases, struct {
			method, path, body, origin, csrf, cookie string
			status                                   int
		}{"PUT", "/api/me/program", body, "http://127.0.0.1:5173", strings.Repeat("c", 64), strings.Repeat("s", 43), 422})
	}
	for _, tc := range cases {
		fake := &fakeProfile{}
		handler := presentation.NewProfileHandler(fake, "http://127.0.0.1:5173", http.NotFoundHandler())
		req := httptest.NewRequest(tc.method, tc.path, strings.NewReader(tc.body))
		req.Header.Set("Origin", tc.origin)
		req.Header.Set("X-CSRF-Token", tc.csrf)
		req.Header.Set("Content-Type", "application/json")
		if tc.cookie != "" {
			req.AddCookie(&http.Cookie{Name: "grad_checker_session", Value: tc.cookie})
		}
		recorder := httptest.NewRecorder()
		handler.ServeHTTP(recorder, req)
		if recorder.Code != tc.status || len(fake.calls) != 0 {
			t.Fatalf("%s %s %s: %d %s", tc.method, tc.path, tc.body, recorder.Code, recorder.Body.String())
		}
	}
}

func TestProfileMapsBusinessErrors(t *testing.T) {
	for code, status := range map[string]int{"invalid_credentials": 401, "invalid_csrf": 403, "invalid_program": 422, "revision_conflict": 409, "profile_unavailable": 503} {
		fake := &fakeProfile{err: &ports.AuthError{Code: code}}
		handler := presentation.NewProfileHandler(fake, "http://127.0.0.1:5173", http.NotFoundHandler())
		req := httptest.NewRequest("GET", "/api/me", nil)
		req.AddCookie(&http.Cookie{Name: "grad_checker_session", Value: strings.Repeat("s", 43)})
		recorder := httptest.NewRecorder()
		handler.ServeHTTP(recorder, req)
		if recorder.Code != status || !strings.Contains(recorder.Body.String(), `"detail"`) {
			t.Fatal(code, recorder.Code, recorder.Body.String())
		}
		if fake.calls[0].Token != strings.Repeat("s", 43) {
			t.Fatal("session was not forwarded")
		}
	}
}

func TestProfileClientValidatesBridgeResponse(t *testing.T) {
	for _, body := range []string{
		`{"data":{"profile":{"student_id":"own","login_name":"owner","program_id":null,"curriculum_id":null,"data_revision":0}}}`,
		`{"data":{"profile":{}}}`, `{"data":{}}`, `{"data":null}`, `{"data":{"programs":[]}}`,
		`{"data":{"profile":{"student_id":"own","login_name":"owner","data_revision":-1}}}`,
		`{"data":{},"error":{"code":"revision_conflict"}}`,
	} {
		server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if r.URL.Path != "/bridge/profile" {
				t.Error(r.URL.Path)
			}
			var call ports.ProfileCall
			if json.NewDecoder(r.Body).Decode(&call) != nil || call.Operation != "me" {
				t.Error("invalid call")
			}
			_, _ = w.Write([]byte(body))
		}))
		client, err := infrastructure.NewPythonProfileClient(server.URL)
		if err != nil {
			t.Fatal(err)
		}
		_, err = client.Call(context.Background(), ports.ProfileCall{Operation: "me", Token: strings.Repeat("s", 43)})
		if (err == nil) != strings.Contains(body, `"data_revision":0`) {
			t.Fatalf("%s: %v", body, err)
		}
		server.Close()
	}
}

// 本人データを更新するAPIは、Content-Typeの不正を成績保存と同じく415で返す。
func TestProfileRejectsNonJSONContentType(t *testing.T) {
	fake := &fakeProfile{}
	handler := presentation.NewProfileHandler(fake, "http://127.0.0.1:5173", http.NotFoundHandler())
	body := `{"program_id":"00000000-0000-4000-8000-000000000001","curriculum_id":"00000000-0000-4000-8000-000000000002","expected_revision":0}`
	req := httptest.NewRequest("PUT", "/api/me/program", strings.NewReader(body))
	req.Header.Set("Origin", "http://127.0.0.1:5173")
	req.Header.Set("X-CSRF-Token", strings.Repeat("c", 64))
	req.Header.Set("Content-Type", "text/plain")
	req.AddCookie(&http.Cookie{Name: "grad_checker_session", Value: strings.Repeat("s", 43)})
	recorder := httptest.NewRecorder()
	handler.ServeHTTP(recorder, req)
	if recorder.Code != 415 || len(fake.calls) != 0 {
		t.Fatalf("%d %s", recorder.Code, recorder.Body.String())
	}
}

// 成績・所属・科目で同じ業務エラーコードは同じHTTPステータスに変換する。
func TestSharedBusinessErrorsMapConsistently(t *testing.T) {
	for code, status := range map[string]int{"profile_not_found": 401, "revision_conflict": 409, "profile_unavailable": 503} {
		fake := &fakeProfile{err: &ports.AuthError{Code: code}}
		handler := presentation.NewProfileHandler(fake, "http://127.0.0.1:5173", http.NotFoundHandler())
		req := httptest.NewRequest("GET", "/api/me", nil)
		req.AddCookie(&http.Cookie{Name: "grad_checker_session", Value: strings.Repeat("s", 43)})
		recorder := httptest.NewRecorder()
		handler.ServeHTTP(recorder, req)
		if recorder.Code != status {
			t.Fatal(code, recorder.Code, recorder.Body.String())
		}
	}
}
