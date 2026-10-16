package infrastructure

import (
	"context"
	"time"

	"grad-checker/backend/modules/accounts/application"
	"grad-checker/backend/modules/shared/internalhttp"
)

type PythonAuthClient struct {
	client *internalhttp.Client
}

func NewPythonAuthClient(origin string) (*PythonAuthClient, error) {
	client, err := internalhttp.New(origin, "/internal/auth", 10*time.Second, 16384)
	if err != nil {
		return nil, err
	}
	return &PythonAuthClient{client}, nil
}
func (c *PythonAuthClient) Call(ctx context.Context, call application.AuthCall) (application.AuthResult, error) {
	var empty application.AuthResult
	raw, err := c.client.Call(ctx, call)
	if err != nil {
		return empty, accountError(err)
	}
	var data application.AuthResult
	if internalhttp.DecodeData(raw, &data) != nil {
		return empty, application.ErrBackend
	}
	switch call.Operation {
	case "config":
		if data.Policy == nil || data.Policy.PasswordMinLength < 12 || data.Policy.PasswordMaxLength < data.Policy.PasswordMinLength {
			return empty, application.ErrBackend
		}
	case "register":
		if !data.Registered || len(data.RecoveryCode) != 43 {
			return empty, application.ErrBackend
		}
	case "recover":
		if !data.Recovered || len(data.RecoveryCode) != 43 {
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
