package tests

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"grad-checker/backend/apps/api/controllers"
	"grad-checker/backend/modules/grades/application/ports"
	"grad-checker/backend/modules/grades/infrastructure/external_services"
)

type fakeGrades struct {
	calls []ports.GradeCall
	err   error
}

func (f *fakeGrades) Call(_ context.Context, call ports.GradeCall) (ports.StudentGrades, error) {
	f.calls = append(f.calls, call)
	return ports.StudentGrades{Grades: []ports.GradeAttempt{}}, f.err
}

const validAttempt = `{"course_id":"00000000-0000-4000-8000-000000000001","attempt_no":1,"result_status":"finalized","grade_code":"A","academic_year":2026,"term_code":"first"}`
const validGradeSet = `{"expected_revision":0,"grades":[` + validAttempt + `]}`

func gradeRequest(method, body, contentType string) *http.Request {
	req := httptest.NewRequest(method, "/api/me/grades", strings.NewReader(body))
	req.Header.Set("Origin", "http://127.0.0.1:5173")
	req.Header.Set("X-CSRF-Token", strings.Repeat("c", 64))
	req.Header.Set("Content-Type", contentType)
	req.AddCookie(&http.Cookie{Name: "grad_checker_session", Value: strings.Repeat("s", 43)})
	return req
}

func TestGradesRejectInvalidInputBeforeBackend(t *testing.T) {
	replace := func(old, new string) string { return strings.Replace(validGradeSet, old, new, 1) }
	invalid := []string{
		`{}`, `null`, `[]`, validGradeSet + `{}`, `{"expected_revision":0}`,
		`{"expected_revision":0,"grades":null}`,
		replace(`"expected_revision":0`, `"expected_revision":-1`),
		replace(`"expected_revision":0`, `"expected_revision":1.5`),
		replace(`"expected_revision":0`, `"expected_revision":0,"expected_revision":1`),
		replace(`"expected_revision":0`, `"expected_revision":0,"student_id":"other"`),
		replace(`"course_id":"00000000-0000-4000-8000-000000000001"`, `"course_id":"unknown"`),
		replace(`"course_id":"00000000-0000-4000-8000-000000000001"`, `"course_id":null`),
		replace(`"attempt_no":1`, `"attempt_no":0`),
		replace(`"attempt_no":1`, `"attempt_no":21`),
		replace(`"attempt_no":1`, `"attempt_no":true`),
		replace(`"result_status":"finalized"`, `"result_status":"passed"`),
		replace(`"grade_code":"A"`, `"grade_code":"R"`),
		replace(`"grade_code":"A"`, `"grade_code":null`),
		replace(`"result_status":"finalized"`, `"result_status":"pending"`),
		replace(`"academic_year":2026`, `"academic_year":1899`),
		replace(`"academic_year":2026`, `"academic_year":"2026"`),
		replace(`"term_code":"first"`, `"term_code":"summer"`),
		replace(`,"term_code":"first"`, ``),
		replace(`"term_code":"first"`, `"term_code":"first","credits":4`),
		replace(`"term_code":"first"`, `"term_code":"first","term_code":"second"`),
	}
	cases := []struct {
		req    *http.Request
		status int
	}{
		{httptest.NewRequest("GET", "/api/me/grades", nil), 401},
		{gradeRequest("POST", validGradeSet, "application/json"), 405},
		{gradeRequest("PUT", validGradeSet, "text/plain"), 415},
		{gradeRequest("PUT", strings.Repeat(" ", 256<<10+1), "application/json"), 413},
	}
	query := gradeRequest("GET", "", "")
	query.URL.RawQuery = "student_id=other"
	cases = append(cases, struct {
		req    *http.Request
		status int
	}{query, 422})
	for _, origin := range []string{"https://evil.example", ""} {
		req := gradeRequest("PUT", validGradeSet, "application/json")
		req.Header.Set("Origin", origin)
		cases = append(cases, struct {
			req    *http.Request
			status int
		}{req, 403})
	}
	noCSRF := gradeRequest("PUT", validGradeSet, "application/json")
	noCSRF.Header.Del("X-CSRF-Token")
	cases = append(cases, struct {
		req    *http.Request
		status int
	}{noCSRF, 403})
	for _, body := range invalid {
		cases = append(cases, struct {
			req    *http.Request
			status int
		}{gradeRequest("PUT", body, "application/json"), 422})
	}
	for _, tc := range cases {
		fake := &fakeGrades{}
		recorder := httptest.NewRecorder()
		controllers.NewGradeHandler(fake, "http://127.0.0.1:5173", http.NotFoundHandler()).ServeHTTP(recorder, tc.req)
		if recorder.Code != tc.status || len(fake.calls) != 0 || recorder.Header().Get("Cache-Control") != "no-store" {
			t.Fatalf("%s: %d %s", tc.req.Method, recorder.Code, recorder.Body.String())
		}
	}
}

func TestGradesForwardNormalizedSet(t *testing.T) {
	fake := &fakeGrades{}
	body := strings.Replace(validGradeSet, "00000000-0000-4000-8000-000000000001", "{00000000-0000-4000-8000-00000000000A}", 1)
	body = strings.Replace(body, `]`, `,{"course_id":"00000000-0000-4000-8000-000000000002","attempt_no":1,"result_status":"pending","grade_code":null,"academic_year":null,"term_code":null}]`, 1)
	recorder := httptest.NewRecorder()
	controllers.NewGradeHandler(fake, "http://127.0.0.1:5173", http.NotFoundHandler()).ServeHTTP(recorder, gradeRequest("PUT", body, "application/json; charset=utf-8"))
	if recorder.Code != 200 || len(fake.calls) != 1 {
		t.Fatal(recorder.Code, recorder.Body.String())
	}
	call := fake.calls[0]
	if call.Operation != "save" || call.CSRF != strings.Repeat("c", 64) || call.Token != strings.Repeat("s", 43) || len(call.GradeSet.Grades) != 2 {
		t.Fatalf("%+v", call)
	}
	first, second := call.GradeSet.Grades[0], call.GradeSet.Grades[1]
	if first.CourseID != "00000000-0000-4000-8000-00000000000a" || *first.GradeCode != "A" || *first.AcademicYear != 2026 || second.GradeCode != nil || second.TermCode != nil {
		t.Fatalf("%+v %+v", first, second)
	}
	if strings.TrimSpace(recorder.Body.String()) != `{"grades":[],"data_revision":0}` {
		t.Fatal(recorder.Body.String())
	}
}

func TestGradesMapBusinessErrors(t *testing.T) {
	for code, status := range map[string]int{
		"invalid_credentials": 401, "invalid_csrf": 403, "student_not_found": 401, "unknown_course": 400,
		"duplicate_attempt": 422, "invalid_attempt_sequence": 422, "revision_conflict": 409,
		"grades_unavailable": 503, "unexpected": 502,
	} {
		fake := &fakeGrades{err: &ports.GradeError{Code: code}}
		recorder := httptest.NewRecorder()
		controllers.NewGradeHandler(fake, "http://127.0.0.1:5173", http.NotFoundHandler()).ServeHTTP(recorder, gradeRequest("PUT", validGradeSet, "application/json"))
		if recorder.Code != status || !strings.Contains(recorder.Body.String(), `"detail"`) {
			t.Fatal(code, recorder.Code, recorder.Body.String())
		}
	}
}

func TestGradeClientValidatesBridgeResponse(t *testing.T) {
	valid := `{"data":{"grades":[{"course_id":"c","attempt_no":1,"result_status":"pending","grade_code":null,"academic_year":null,"term_code":null}],"data_revision":1}}`
	for body, ok := range map[string]bool{
		valid: true,
		`{"data":{"grades":[],"data_revision":1}}`:                                            false,
		`{"data":{"grades":null,"data_revision":1}}`:                                          false,
		`{"data":{"grades":[],"data_revision":-1}}`:                                           false,
		`{"data":{"grades":[],"data_revision":1,"extra":true}}`:                               false,
		strings.Replace(valid, `"result_status":"pending"`, `"result_status":"finalized"`, 1): false,
		`{"error":{"code":"revision_conflict"}}`:                                              false,
		`{"error":{"code":""}}`:                                                               false,
		`{"data":{"grades":[],"data_revision":1},"error":{"code":"x"}}`:                       false,
	} {
		server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			var call ports.GradeCall
			if r.URL.Path != "/bridge/grades" || json.NewDecoder(r.Body).Decode(&call) != nil || call.Operation != "save" || call.GradeSet == nil {
				t.Error("invalid call")
			}
			_, _ = w.Write([]byte(body))
		}))
		client, err := infrastructure.NewPythonGradeClient(server.URL)
		if err != nil {
			t.Fatal(err)
		}
		set := &ports.GradeSet{Grades: []ports.GradeAttempt{{CourseID: "c", AttemptNo: 1, ResultStatus: "pending"}}}
		_, err = client.Call(context.Background(), ports.GradeCall{Operation: "save", Token: strings.Repeat("s", 43), CSRF: strings.Repeat("c", 64), GradeSet: set})
		if (err == nil) != ok {
			t.Fatalf("%s: %v", body, err)
		}
		server.Close()
	}
}
