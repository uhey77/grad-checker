package infrastructure

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/url"
	"time"

	"grad-checker/backend/modules/accounts/application"
)

type PythonAuthClient struct {
	endpoint string
	client   *http.Client
}

func NewPythonAuthClient(origin string) (*PythonAuthClient, error) {
	u, err := url.Parse(origin)
	if err != nil || u.Host == "" || (u.Scheme != "http" && u.Scheme != "https") || u.User != nil || u.Path != "" || u.RawQuery != "" || u.Fragment != "" {
		return nil, errors.New("python-urlにはhttp/httpsオリジンを指定してください。")
	}
	return &PythonAuthClient{origin + "/internal/auth", &http.Client{Timeout: 10 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}}, nil
}
func (c *PythonAuthClient) Call(ctx context.Context, call application.AuthCall) (application.AuthResult, error) {
	var empty application.AuthResult
	body, err := json.Marshal(call)
	if err != nil {
		return empty, application.ErrBackend
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.endpoint, bytes.NewReader(body))
	if err != nil {
		return empty, application.ErrBackend
	}
	req.Header.Set("Content-Type", "application/json")
	response, err := c.client.Do(req)
	if err != nil {
		return empty, application.ErrBackend
	}
	defer response.Body.Close()
	if response.StatusCode != 200 {
		return empty, application.ErrBackend
	}
	var result struct {
		Data  *application.AuthResult `json:"data"`
		Error *application.AuthError  `json:"error"`
	}
	decoder := json.NewDecoder(io.LimitReader(response.Body, 16384))
	decoder.DisallowUnknownFields()
	if decoder.Decode(&result) != nil {
		return empty, application.ErrBackend
	}
	var extra any
	if decoder.Decode(&extra) != io.EOF || (result.Data == nil) == (result.Error == nil) {
		return empty, application.ErrBackend
	}
	if result.Error != nil {
		return empty, result.Error
	}
	data := *result.Data
	switch call.Operation {
	case "config":
		if data.Policy == nil || data.Policy.PasswordMinLength < 12 || data.Policy.PasswordMaxLength < data.Policy.PasswordMinLength || data.Policy.VerificationMinutes < 1 {
			return empty, application.ErrBackend
		}
	case "register":
		if !data.Accepted {
			return empty, application.ErrBackend
		}
	case "verify":
		if !data.Verified {
			return empty, application.ErrBackend
		}
	case "login", "session":
		if !data.Authenticated || data.Student == nil || data.Student.ID == "" || data.Student.LoginName == "" || len(data.CSRFToken) != 64 {
			return empty, application.ErrBackend
		}
		if _, err := time.Parse(time.RFC3339, data.ExpiresAt); err != nil {
			return empty, application.ErrBackend
		}
		if call.Operation == "login" && len(data.SessionToken) != 43 {
			return empty, application.ErrBackend
		}
	case "logout":
		if data.Authenticated {
			return empty, application.ErrBackend
		}
	default:
		return empty, application.ErrBackend
	}
	return data, nil
}
