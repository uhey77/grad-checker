package tests

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"grad-checker/backend/api/presentation"
	"grad-checker/backend/modules/subjects/application/ports"
	"grad-checker/backend/modules/subjects/infrastructure"
)

type fakeCatalog struct {
	calls []ports.CourseCatalogCall
	err   error
}

func (f *fakeCatalog) Call(_ context.Context, call ports.CourseCatalogCall) (json.RawMessage, error) {
	f.calls = append(f.calls, call)
	return json.RawMessage(`{"curriculum":{"curriculum_id":"c"},"courses":[]}`), f.err
}

func courseRequest(target string) *http.Request {
	req := httptest.NewRequest("GET", target, nil)
	req.AddCookie(&http.Cookie{Name: "grad_checker_session", Value: strings.Repeat("s", 43)})
	return req
}

func TestCoursesRejectInvalidQueriesBeforeBackend(t *testing.T) {
	cases := map[string]int{
		"/api/categories?q=x":                        422,
		"/api/courses?term=first":                    422,
		"/api/courses?q=":                            422,
		"/api/courses?q=a&q=b":                       422,
		"/api/courses?q=" + strings.Repeat("あ", 101): 422,
		"/api/courses?semester=summer":               422,
		"/api/courses?category_id=unknown":           422,
		"/api/courses?q=%zz":                         422,
		"/api/courses?q=a;faculty=b":                 422,
	}
	for target, status := range cases {
		fake := &fakeCatalog{}
		recorder := httptest.NewRecorder()
		presentation.NewCourseHandler(fake, http.NotFoundHandler()).ServeHTTP(recorder, courseRequest(target))
		if recorder.Code != status || len(fake.calls) != 0 {
			t.Fatalf("%s: %d %s", target, recorder.Code, recorder.Body.String())
		}
	}
	for _, req := range []*http.Request{httptest.NewRequest("GET", "/api/courses", nil), httptest.NewRequest("POST", "/api/categories", nil)} {
		fake := &fakeCatalog{}
		if req.Method == "POST" {
			req.AddCookie(&http.Cookie{Name: "grad_checker_session", Value: strings.Repeat("s", 43)})
		}
		recorder := httptest.NewRecorder()
		presentation.NewCourseHandler(fake, http.NotFoundHandler()).ServeHTTP(recorder, req)
		if recorder.Code != map[string]int{"GET": 401, "POST": 405}[req.Method] || len(fake.calls) != 0 {
			t.Fatal(req.Method, recorder.Code)
		}
	}
}

func TestCoursesForwardFilters(t *testing.T) {
	fake := &fakeCatalog{}
	recorder := httptest.NewRecorder()
	target := "/api/courses?category_id=00000000-0000-4000-8000-00000000000A&faculty=%E5%AD%A6%E9%83%A8&department=d&semester=first&q=AI"
	presentation.NewCourseHandler(fake, http.NotFoundHandler()).ServeHTTP(recorder, courseRequest(target))
	if recorder.Code != 200 || recorder.Header().Get("Cache-Control") != "no-store" || len(fake.calls) != 1 {
		t.Fatal(recorder.Code, recorder.Body.String())
	}
	want := ports.CourseFilters{CategoryID: "00000000-0000-4000-8000-00000000000a", Faculty: "学部", Department: "d", Semester: "first", Q: "AI"}
	if call := fake.calls[0]; call.Operation != "courses" || call.Token != strings.Repeat("s", 43) || *call.Filters != want {
		t.Fatalf("%+v", call)
	}
	fake = &fakeCatalog{}
	presentation.NewCourseHandler(fake, http.NotFoundHandler()).ServeHTTP(httptest.NewRecorder(), courseRequest("/api/categories"))
	if fake.calls[0].Operation != "categories" || fake.calls[0].Filters != nil {
		t.Fatalf("%+v", fake.calls[0])
	}
}

func TestCoursesMapBusinessErrors(t *testing.T) {
	for code, status := range map[string]int{
		"invalid_credentials": 401, "profile_not_found": 401, "program_not_selected": 409, "unknown_category": 422,
		"curriculum_not_found": 409, "classification_inconsistent": 409, "catalog_unavailable": 503, "unexpected": 502,
	} {
		fake := &fakeCatalog{err: &ports.CourseCatalogError{Code: code}}
		recorder := httptest.NewRecorder()
		presentation.NewCourseHandler(fake, http.NotFoundHandler()).ServeHTTP(recorder, courseRequest("/api/courses"))
		if recorder.Code != status || !strings.Contains(recorder.Body.String(), `"detail"`) {
			t.Fatal(code, recorder.Code, recorder.Body.String())
		}
	}
	fake := &fakeCatalog{err: ports.ErrTimeout}
	recorder := httptest.NewRecorder()
	presentation.NewCourseHandler(fake, http.NotFoundHandler()).ServeHTTP(recorder, courseRequest("/api/categories"))
	if recorder.Code != 504 {
		t.Fatal(recorder.Code)
	}
}

func TestCourseCatalogClientValidatesBridgeResponse(t *testing.T) {
	for _, tc := range []struct {
		operation, body string
		ok              bool
	}{
		{"courses", `{"data":{"curriculum":{"curriculum_id":"c"},"courses":[]}}`, true},
		{"categories", `{"data":{"curriculum":{"curriculum_id":"c"},"categories":[]}}`, true},
		{"courses", `{"data":{"curriculum":{"curriculum_id":"c"},"categories":[]}}`, false},
		{"courses", `{"data":{"curriculum":{"curriculum_id":"c"},"courses":null}}`, false},
		{"courses", `{"data":{"courses":[]}}`, false},
		{"courses", `{"data":[]}`, false},
		{"courses", `{"error":{"code":"program_not_selected"}}`, false},
		{"courses", `{"error":{"code":""}}`, false},
	} {
		server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			var call ports.CourseCatalogCall
			if r.URL.Path != "/bridge/courses" || json.NewDecoder(r.Body).Decode(&call) != nil || call.Operation != tc.operation {
				t.Error("invalid call")
			}
			_, _ = w.Write([]byte(tc.body))
		}))
		client, err := infrastructure.NewPythonCourseCatalogClient(server.URL, time.Second)
		if err != nil {
			t.Fatal(err)
		}
		_, err = client.Call(context.Background(), ports.CourseCatalogCall{Operation: tc.operation, Token: strings.Repeat("s", 43)})
		if (err == nil) != tc.ok {
			t.Fatalf("%s %s: %v", tc.operation, tc.body, err)
		}
		server.Close()
	}
}
