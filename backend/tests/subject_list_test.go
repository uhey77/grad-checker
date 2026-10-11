package tests

import (
	"context"
	"encoding/json"
	"errors"
	"net/http/httptest"
	"strings"
	"testing"

	"grad-checker/api/presentation"
	"grad-checker/subjects/application"
)

type fakeSubjectList struct {
	calls int
	id    string
	err   error
}

func (f *fakeSubjectList) ListPrograms(context.Context) (json.RawMessage, error) {
	f.calls++
	return json.RawMessage(`[{"name":"テスト課程"}]`), f.err
}
func (f *fakeSubjectList) GetSubjectList(_ context.Context, id string) (json.RawMessage, error) {
	f.calls++
	f.id = id
	return json.RawMessage(`{"program":{"name":"テスト課程"},"courses":[]}`), f.err
}

func TestExternalValidationDoesNotCallPython(t *testing.T) {
	for _, tc := range []struct {
		method, path string
		preview      bool
		status       int
	}{
		{"GET", "/api/dev/subject-list/invalid", true, 422},
		{"GET", "/api/dev/subject-list/programs", false, 404},
		{"POST", "/api/dev/subject-list/programs", true, 405},
		{"GET", "/internal/subject-list", true, 404},
		{"GET", "/api/dev/subject-list/id/extra", true, 404},
		{"GET", "/api/health", true, 200},
	} {
		f := &fakeSubjectList{}
		w := httptest.NewRecorder()
		presentation.NewSubjectListHandler(f, tc.preview).ServeHTTP(w, httptest.NewRequest(tc.method, tc.path, nil))
		if w.Code != tc.status || f.calls != 0 {
			t.Errorf("%s %s: code=%d calls=%d", tc.method, tc.path, w.Code, f.calls)
		}
		if w.Header().Get("Cache-Control") != "no-store" {
			t.Error("missing no-store")
		}
		if tc.status == 405 && w.Header().Get("Allow") != "GET" {
			t.Error("missing Allow")
		}
	}
}

func TestUUIDNormalizationAndResponse(t *testing.T) {
	canonical := "92e775e5-2873-5f6e-86d8-3e3a20124330"
	for _, id := range []string{canonical, strings.ToUpper(canonical), strings.ReplaceAll(canonical, "-", ""), "{" + canonical + "}", "urn:uuid:" + canonical} {
		f := &fakeSubjectList{}
		w := httptest.NewRecorder()
		presentation.NewSubjectListHandler(f, true).ServeHTTP(w, httptest.NewRequest("GET", "/api/dev/subject-list/"+id, nil))
		if w.Code != 200 || f.id != canonical {
			t.Fatalf("%s: code=%d normalized=%s", id, w.Code, f.id)
		}
		var result map[string]any
		if err := json.Unmarshal(w.Body.Bytes(), &result); err != nil {
			t.Fatal(err)
		}
		if result["program"] == nil || result["data"] != nil {
			t.Fatal("internal envelope leaked")
		}
	}
}

func TestErrorCodesBecomeExternalErrors(t *testing.T) {
	for _, tc := range []struct {
		err    error
		status int
		detail string
	}{
		{&application.SubjectListError{Code: "curriculum_not_found"}, 404, "選択したカリキュラムが見つかりません。"},
		{&application.SubjectListError{Code: "classification_inconsistent"}, 409, "科目分類のデータが不整合です。課程・科目データを確認してください。"},
		{&application.SubjectListError{Code: "subject_list_unavailable"}, 503, "科目データを読み込めません。時間をおいて再試行してください。"},
		{&application.SubjectListError{Code: "internal_error"}, 500, "科目データの取得中に予期しないエラーが発生しました。"},
		{&application.SubjectListError{Code: "invalid_request"}, 502, "Pythonサービスの応答を読み込めません。"},
		{application.ErrUnavailable, 502, "Pythonサービスに接続できません。起動状態を確認してください。"},
		{application.ErrTimeout, 504, "Pythonサービスの応答がタイムアウトしました。"},
		{errors.New("SELECT private internal details"), 502, "Pythonサービスの応答を読み込めません。"},
	} {
		f := &fakeSubjectList{err: tc.err}
		w := httptest.NewRecorder()
		presentation.NewSubjectListHandler(f, true).ServeHTTP(w, httptest.NewRequest("GET", "/api/dev/subject-list/programs", nil))
		var result map[string]string
		if err := json.Unmarshal(w.Body.Bytes(), &result); err != nil {
			t.Fatal(err)
		}
		if w.Code != tc.status || result["detail"] != tc.detail {
			t.Errorf("%v: code=%d body=%s", tc.err, w.Code, w.Body.String())
		}
	}
}
