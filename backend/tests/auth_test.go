package tests

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"grad-checker/backend/api/presentation"
	"grad-checker/backend/modules/accounts/application"
)

type fakeAuth struct {
	calls  []application.AuthCall
	result application.AuthResult
	err    error
}

func (f *fakeAuth) Call(_ context.Context, call application.AuthCall) (application.AuthResult, error) {
	f.calls = append(f.calls, call)
	return f.result, f.err
}

func TestAuthLoginSecureCookieAndNoTokenInBody(t *testing.T) {
	fake := &fakeAuth{result: application.AuthResult{Authenticated: true, SessionToken: strings.Repeat("s", 43), CSRFToken: strings.Repeat("c", 64), ExpiresAt: time.Now().Add(time.Hour).Format(time.RFC3339), Student: &application.Student{ID: "id", LoginName: "student@edu.teu.ac.jp"}}}
	handler, err := presentation.NewAuthHandler(fake, "https://checker.example", http.NotFoundHandler())
	if err != nil {
		t.Fatal(err)
	}
	req := httptest.NewRequest("POST", "/api/auth/login", strings.NewReader(`{"email":"student@edu.teu.ac.jp","password":"app-password"}`))
	req.Header.Set("Origin", "https://checker.example")
	req.Header.Set("Content-Type", "application/json")
	recorder := httptest.NewRecorder()
	handler.ServeHTTP(recorder, req)
	if recorder.Code != 200 {
		t.Fatal(recorder.Body.String())
	}
	cookie := recorder.Result().Cookies()[0]
	if !cookie.HttpOnly || !cookie.Secure || cookie.SameSite != http.SameSiteLaxMode || cookie.Path != "/" {
		t.Fatalf("Invalid cookie flags")
	}
	if strings.Contains(recorder.Body.String(), "session_token") || strings.Contains(recorder.Body.String(), strings.Repeat("s", 43)) {
		t.Fatal("Session token was exposed")
	}
	if fake.calls[0].ClientKey != "192.0.2.1" {
		t.Fatalf("Unexpected client identity %s", fake.calls[0].ClientKey)
	}
}

func TestAuthRejectsInvalidExternalCallsBeforeBackend(t *testing.T) {
	cases := []struct {
		method, path, body, origin string
		status                     int
	}{
		{"POST", "/api/auth/register", `{"email":"x@edu.teu.ac.jp"}`, "https://evil.example", 403},
		{"POST", "/api/auth/register", `{"email":"x@edu.teu.ac.jp","email":"y@edu.teu.ac.jp"}`, "http://127.0.0.1:5173", 422},
		{"POST", "/api/auth/register", `{"email":"x@edu.teu.ac.jp","password":"hijack"}`, "http://127.0.0.1:5173", 422},
		{"POST", "/api/auth/register", `{"email":null}`, "http://127.0.0.1:5173", 422},
		{"POST", "/api/auth/register", `{"email":"x@edu.teu.ac.jp"} {}`, "http://127.0.0.1:5173", 422},
		{"GET", "/api/auth/register", "", "", 405},
		{"GET", "/api/auth/session?student_id=other", "", "", 422},
		{"GET", "/api/auth/session", "", "", 401},
		{"POST", "/api/auth/logout", `{}`, "http://127.0.0.1:5173", 401},
	}
	for _, tc := range cases {
		fake := &fakeAuth{}
		handler, err := presentation.NewAuthHandler(fake, "http://127.0.0.1:5173", http.NotFoundHandler())
		if err != nil {
			t.Fatal(err)
		}
		req := httptest.NewRequest(tc.method, tc.path, strings.NewReader(tc.body))
		req.Header.Set("Origin", tc.origin)
		req.Header.Set("Content-Type", "application/json")
		recorder := httptest.NewRecorder()
		handler.ServeHTTP(recorder, req)
		if recorder.Code != tc.status || len(fake.calls) != 0 {
			t.Fatalf("%s %s: status=%d calls=%d", tc.method, tc.path, recorder.Code, len(fake.calls))
		}
	}
}

func TestAuthIgnoresSpoofedForwardedIPAndMapsErrors(t *testing.T) {
	fake := &fakeAuth{err: &application.AuthError{Code: "rate_limited"}}
	handler, err := presentation.NewAuthHandler(fake, "http://127.0.0.1:5173", http.NotFoundHandler())
	if err != nil {
		t.Fatal(err)
	}
	req := httptest.NewRequest("POST", "/api/auth/register", strings.NewReader(`{"email":"x@edu.teu.ac.jp"}`))
	req.Header.Set("Origin", "http://127.0.0.1:5173")
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Forwarded-For", "spoofed")
	recorder := httptest.NewRecorder()
	handler.ServeHTTP(recorder, req)
	if recorder.Code != 429 || fake.calls[0].ClientKey != "192.0.2.1" {
		t.Fatal("Rate limit or client identity mismatch")
	}
}
