package tests

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"grad-checker/backend/modules/subjects/application/ports"
	"grad-checker/backend/modules/subjects/infrastructure"
)

func TestBridgeProtocol(t *testing.T) {
	for _, tc := range []struct {
		body   string
		status int
		code   string
		valid  bool
	}{
		{`{"data":[]}`, 200, "", true},
		{`{"error":{"code":"subject_list_unavailable","detail":"SQL secret"}}`, 200, "subject_list_unavailable", false},
		{`{"data":[],"error":{"code":"subject_list_unavailable"}}`, 200, "", false},
		{`{"data":null}`, 200, "", false},
		{`{"data":{}}`, 200, "", false},
		{`{"detail":"SQL secret"}`, 503, "", false},
		{`not json`, 200, "", false},
		{`{"data":[]} {}`, 200, "", false},
	} {
		python := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if r.Method != "POST" || r.URL.Path != "/bridge/subject-list" || r.Header.Get("Content-Type") != "application/json" {
				t.Errorf("unexpected bridge request: %v", r)
			}
			var call map[string]string
			if err := json.NewDecoder(r.Body).Decode(&call); err != nil {
				t.Error(err)
			}
			if call["operation"] != "list_programs" {
				t.Error("unexpected operation")
			}
			w.WriteHeader(tc.status)
			_, _ = w.Write([]byte(tc.body))
		}))
		client, err := infrastructure.NewPythonSubjectListClient(python.URL, time.Second)
		if err != nil {
			t.Fatal(err)
		}
		data, err := client.ListPrograms(context.Background())
		python.Close()
		if tc.valid {
			if err != nil || string(data) != "[]" {
				t.Fatalf("unexpected success result %s %v", data, err)
			}
			continue
		}
		if tc.code != "" {
			var business *ports.SubjectListError
			if !errors.As(err, &business) || business.Code != tc.code {
				t.Fatalf("unexpected error %v", err)
			}
		} else if !errors.Is(err, ports.ErrProtocol) {
			t.Fatalf("expected protocol error, got %v", err)
		}
	}
}

func TestBridgeTimeoutAndCancellation(t *testing.T) {
	python := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = io.Copy(io.Discard, r.Body)
		select {
		case <-r.Context().Done():
		case <-time.After(time.Second):
		}
	}))
	defer python.Close()
	client, _ := infrastructure.NewPythonSubjectListClient(python.URL, 20*time.Millisecond)
	_, err := client.ListPrograms(context.Background())
	if !errors.Is(err, ports.ErrTimeout) {
		t.Fatalf("got %v", err)
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	start := time.Now()
	_, err = client.ListPrograms(ctx)
	if err == nil || time.Since(start) > time.Second {
		t.Fatal("cancellation ignored")
	}
}

func TestBridgeConnectionFailure(t *testing.T) {
	client, _ := infrastructure.NewPythonSubjectListClient("http://127.0.0.1:1", time.Second)
	_, err := client.ListPrograms(context.Background())
	if !errors.Is(err, ports.ErrUnavailable) {
		t.Fatalf("got %v", err)
	}
}
