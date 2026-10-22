package infrastructure

import (
	"context"
	"time"

	"grad-checker/backend/modules/accounts/application/ports"
	"grad-checker/backend/shared/pythonbridge"
)

type PythonAuthClient struct {
	client *pythonbridge.Client
}

func NewPythonAuthClient(origin string) (*PythonAuthClient, error) {
	client, err := pythonbridge.New(origin, "/bridge/auth", 10*time.Second, 16384)
	if err != nil {
		return nil, err
	}
	return &PythonAuthClient{client}, nil
}
func (c *PythonAuthClient) Call(ctx context.Context, call ports.AuthCall) (ports.AuthResult, error) {
	var empty ports.AuthResult
	raw, err := c.client.Call(ctx, call)
	if err != nil {
		return empty, accountError(err)
	}
	var data ports.AuthResult
	if pythonbridge.DecodeData(raw, &data) != nil {
		return empty, ports.ErrBackend
	}
	switch call.Operation {
	case "config":
		if data.Policy == nil || data.Policy.PasswordMinLength < 12 || data.Policy.PasswordMaxLength < data.Policy.PasswordMinLength {
			return empty, ports.ErrBackend
		}
	case "register":
		if !data.Registered || len(data.RecoveryCode) != 43 {
			return empty, ports.ErrBackend
		}
	case "recover":
		if !data.Recovered || len(data.RecoveryCode) != 43 {
			return empty, ports.ErrBackend
		}
	case "login", "session":
		if !data.Authenticated || data.Student == nil || data.Student.ID == "" || data.Student.LoginName == "" || len(data.CSRFToken) != 64 {
			return empty, ports.ErrBackend
		}
		if _, err := time.Parse(time.RFC3339, data.ExpiresAt); err != nil {
			return empty, ports.ErrBackend
		}
		if call.Operation == "login" && len(data.SessionToken) != 43 {
			return empty, ports.ErrBackend
		}
	case "logout":
		if data.Authenticated {
			return empty, ports.ErrBackend
		}
	default:
		return empty, ports.ErrBackend
	}
	return data, nil
}
